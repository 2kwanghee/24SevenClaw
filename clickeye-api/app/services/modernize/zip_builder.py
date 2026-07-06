"""Modernize ZIP 생성 — `generate_modernize_zip()`.

기존 `app/engine/generator.py.generate_all()` 와 완전히 분리. Modernize 만의 최소 산출:

    project-root/
    ├── .clickeye/linear-issues.json      # 등록된 이슈 매핑 (중복 등록 방지)
    ├── .ralph/tasks/<identifier>.md      # rec.prompt_md → AI 작업 지시
    ├── docs/diagnosis.md                 # CodebaseAnalysis.llm_summary_md
    ├── docs/diagnosis.json               # 분석 결과 머신리더블
    ├── plan.json                         # 태스크 DAG (orchestrator.py 입력)
    ├── scripts/modernize_pipeline.sh     # 오케스트레이터 엔트리 (환경 점검 → orchestrator.py)
    ├── scripts/orchestrator.py           # plan.json 위상정렬 → 웨이브 순차 실행
    ├── MODERNIZE_README.md               # 1-pager 실행 가이드
    └── .env.example                      # LINEAR_API_KEY/TEAM_ID/REPO_URL 안내
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

from app.services.modernize import agent_registry, plan_builder

_TEMPLATES_DIR = Path(__file__).parent / "orchestrator_templates"

_README_TEMPLATE = """# {project_name} — ClickEye Modernize

> GitHub: `{repo_full_name}` | 시나리오: **{scenario}**

## 1. 진단 결과 확인
- `docs/diagnosis.md` — AI 가 분석한 스택·의존성·권장 N건
- `docs/diagnosis.json` — 동일 데이터 머신리더블

## 2. Linear 이슈 확인
- 등록된 이슈 매핑: `.clickeye/linear-issues.json`
- 각 이슈마다 본문에 `prompt_md` 가 포함되며, ZIP 의 `.ralph/tasks/<identifier>.md` 와 동일 내용

## 3. 자동 개발 실행
```bash
cp .env.example .env
# .env 에 LINEAR_API_KEY / LINEAR_TEAM_ID / ANTHROPIC_API_KEY 설정
bash scripts/modernize_pipeline.sh   # plan.json 의 태스크 DAG를 순서대로 실행
```
- `plan.json` — 태스크 DAG (의존성/게이트 정의). `scripts/orchestrator.py` 가 위상정렬 후
  웨이브 단위로 순차 실행한다.
- 옵션: `--dry-run`(실행 순서만 출력), `--resume`(중단 지점부터 재개),
  `--only <task-id>`(단일 태스크만), `--wave <n>`(특정 웨이브만)
- 다른 CLI를 쓰려면 `AGENT_CLI=gemini bash scripts/modernize_pipeline.sh` 처럼 지정

## 4. 결과 확인
- 각 이슈는 `fix/{scenario}/<slug>` 브랜치로 PR 생성
- `harness-gate.sh` (lint/type/test) 통과 시 자동 라벨 `qa-ready`
- 진행 상태는 `.clickeye/state.json` 에 기록됨

## 5. 권장사항 ({recommendation_count} 건)

{recommendation_list}

## 6. Preflight 체크리스트

{preflight_list}
"""

_ENV_EXAMPLE = """# Linear 자동 등록을 위해 사용된 자격증명
LINEAR_API_KEY=<your-linear-api-key>
LINEAR_TEAM_ID={team_id}

# Modernize 대상 저장소
REPO_URL=https://github.com/{repo_full_name}

# AI 코드 작업 시 필요
ANTHROPIC_API_KEY=<sk-ant-...>
"""


def generate_modernize_zip(
    *,
    repo_full_name: str,
    scenario: str,
    session_id: str,
    project_name: str | None = None,
    llm_summary_md: str | None,
    analysis_data: dict[str, Any],
    recommendations: list[dict[str, Any]],
    linear_team_id: str = "",
    linear_issues: list[dict[str, Any]] | None = None,
    target_stack: dict[str, Any] | None = None,
    goals_text: str | None = None,
) -> bytes:
    """ZIP 바이트 반환. 호출자가 file response 로 streaming.

    `target_stack`/`goals_text` 가 주어지면 CE-291 에이전트 매핑 레지스트리를 통해
    요구사항 태그(예: db_migrate)를 도출하고, 태그에 맞는 `.claude/agents/*.md` /
    `.claude/skills/*.md` 를 번들하며 plan.json 태스크에 `assigned_agent` 를 채운다.
    """
    project_name = project_name or repo_full_name.split("/")[-1] or "modernize-project"
    linear_issues = linear_issues or []

    framework_signals = analysis_data.get("framework_signals")
    as_is_db = (
        framework_signals.get("db_type")
        if isinstance(framework_signals, dict)
        else None
    )
    to_be_db = (
        (target_stack.get("db_type") or target_stack.get("db"))
        if isinstance(target_stack, dict)
        else None
    )
    requirement_tags = agent_registry.derive_requirement_tags(
        scenario=scenario, as_is_db=as_is_db, to_be=target_stack, goals_text=goals_text
    )
    resolved_pack = agent_registry.resolve_pack(
        requirement_tags, source_db=as_is_db, target_db=to_be_db
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1) .clickeye/linear-issues.json — Linear 이슈 매핑
        zf.writestr(
            ".clickeye/linear-issues.json",
            json.dumps(
                {
                    "session_id": session_id,
                    "repo_full_name": repo_full_name,
                    "scenario": scenario,
                    "issues": linear_issues,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )

        # 2) .ralph/tasks/<identifier>.md — 각 권장안의 prompt_md
        for rec in recommendations:
            identifier = rec.get("linear_identifier") or rec.get("id") or "unknown"
            # 안전한 파일명 — 영숫자/하이픈만 허용
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(identifier))
            prompt = rec.get("prompt_md") or _fallback_prompt_from_rec(rec)
            zf.writestr(f".ralph/tasks/{safe}.md", prompt)

        # 3) docs/diagnosis.md (LLM 요약)
        diagnosis_md = llm_summary_md or "# 진단 요약\n\n(LLM 요약 없음)"
        zf.writestr("docs/diagnosis.md", diagnosis_md)

        # 4) docs/diagnosis.json (머신리더블)
        zf.writestr(
            "docs/diagnosis.json",
            json.dumps(analysis_data, ensure_ascii=False, indent=2, default=str),
        )

        # 5) MODERNIZE_README.md
        rec_list_md = _build_rec_list_md(recommendations)
        preflight_list_md = _build_preflight_list_md(resolved_pack.preflight_checks)
        zf.writestr(
            "MODERNIZE_README.md",
            _README_TEMPLATE.format(
                project_name=project_name,
                repo_full_name=repo_full_name,
                scenario=scenario,
                recommendation_count=len(recommendations),
                recommendation_list=rec_list_md,
                preflight_list=preflight_list_md,
            ),
        )

        # 6) .env.example
        zf.writestr(
            ".env.example",
            _ENV_EXAMPLE.format(
                team_id=linear_team_id or "<your-linear-team-id>",
                repo_full_name=repo_full_name,
            ),
        )

        # 7) plan.json — 태스크 DAG (orchestrator.py 입력)
        plan = plan_builder.build_plan(
            session_id=session_id,
            repo_full_name=repo_full_name,
            scenario=scenario,
            recommendations=recommendations,
            requirement_tags=requirement_tags,
            source_db=as_is_db,
            target_db=to_be_db,
        )
        zf.writestr("plan.json", json.dumps(plan, ensure_ascii=False, indent=2))

        # 8) scripts/modernize_pipeline.sh + scripts/orchestrator.py — 오케스트레이터
        zf.writestr(
            "scripts/modernize_pipeline.sh",
            (_TEMPLATES_DIR / "modernize_pipeline.sh").read_text(encoding="utf-8"),
        )
        zf.writestr(
            "scripts/orchestrator.py",
            (_TEMPLATES_DIR / "orchestrator.py").read_text(encoding="utf-8"),
        )

        # 9) .claude/agents/*.md + .claude/skills/*.md — 요구사항 태그 기반 에이전트 팩 번들
        written_agents: set[str] = set()
        written_skills: set[str] = set()
        for tag in resolved_pack.tags:
            pack = resolved_pack.packs_by_tag[tag]
            for agent_name in pack.agents:
                if agent_name in written_agents:
                    continue
                written_agents.add(agent_name)
                agent_md = _render_agent_md(agent_name, tag, resolved_pack)
                zf.writestr(f".claude/agents/{agent_name}.md", agent_md)
            for skill_name in pack.skills:
                if skill_name in written_skills:
                    continue
                written_skills.add(skill_name)
                skill_md = _render_skill_md(skill_name, pack.description)
                zf.writestr(f".claude/skills/{skill_name}.md", skill_md)

    buf.seek(0)
    return buf.read()


def _build_rec_list_md(recommendations: list[dict[str, Any]]) -> str:
    if not recommendations:
        return "_(권장사항 없음)_"
    lines: list[str] = []
    for rec in recommendations:
        identifier = rec.get("linear_identifier") or "(미등록)"
        title = rec.get("title", "")
        risk = rec.get("risk", "med")
        effort = rec.get("effort", "M")
        lines.append(f"- `{identifier}` **{title}** — risk: {risk}, effort: {effort}")
    return "\n".join(lines)


def _build_preflight_list_md(checks: list[str]) -> str:
    if not checks:
        return "_(추가 preflight 체크 없음)_"
    return "\n".join(f"- [ ] {c}" for c in checks)


def _render_agent_md(agent_name: str, tag: str, resolved_pack: agent_registry.ResolvedPack) -> str:
    """요구사항 태그 팩의 에이전트 1개를 `.claude/agents/<name>.md` 내용으로 렌더링.

    db_migrate 태그는 소스→타깃 DB 조합별 콤보(주의사항/태스크 시퀀스)를 우선 사용한다.
    """
    pack = resolved_pack.packs_by_tag[tag]
    lines = [
        "---",
        f"name: {agent_name}",
        f"description: {pack.description}",
        "---",
        "",
        f"# {agent_name}",
        "",
        pack.description,
        "",
    ]

    combo = resolved_pack.combo if tag == "db_migrate" else None
    if combo is not None and combo.task_sequence:
        lines.append(f"## 태스크 시퀀스 ({resolved_pack.combo_key})")
        lines.extend(f"{i}. {step}" for i, step in enumerate(combo.task_sequence, start=1))
        lines.append("")
        if combo.notes_md:
            lines.append("## 조합별 주의사항")
            lines.append(combo.notes_md)
            lines.append("")
    elif pack.task_templates:
        lines.append("## 태스크 템플릿")
        lines.extend(f"- {t}" for t in pack.task_templates)
        lines.append("")

    if pack.preflight_checks:
        lines.append("## Preflight 체크리스트")
        lines.extend(f"- [ ] {c}" for c in pack.preflight_checks)
        lines.append("")

    return "\n".join(lines)


def _render_skill_md(skill_name: str, description: str) -> str:
    return (
        "---\n"
        f"name: {skill_name}\n"
        f"description: {description}\n"
        "---\n\n"
        f"# {skill_name}\n\n"
        f"{description}\n"
    )


def _fallback_prompt_from_rec(rec: dict[str, Any]) -> str:
    """rec.prompt_md 가 없을 때 기본 템플릿 생성."""
    title = rec.get("title", "(제목 없음)")
    rationale = rec.get("rationale_md") or ""
    target = rec.get("target_path") or "(대상 파일 미지정)"
    return (
        f"# {title}\n\n"
        f"## Context\n{rationale}\n\n"
        f"## Files in scope\n- `{target}`\n\n"
        f"## Acceptance criteria\n"
        f"- [ ] 변경 사항 적용\n"
        f"- [ ] lint / typecheck / test 통과\n"
    )
