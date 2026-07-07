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

from app.services.modernize import plan_builder

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
) -> bytes:
    """ZIP 바이트 반환. 호출자가 file response 로 streaming."""
    project_name = project_name or repo_full_name.split("/")[-1] or "modernize-project"
    linear_issues = linear_issues or []

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
        zf.writestr(
            "MODERNIZE_README.md",
            _README_TEMPLATE.format(
                project_name=project_name,
                repo_full_name=repo_full_name,
                scenario=scenario,
                recommendation_count=len(recommendations),
                recommendation_list=rec_list_md,
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
        plan = plan_builder.build_orchestrator_plan(
            session_id=session_id,
            repo_full_name=repo_full_name,
            scenario=scenario,
            recommendations=recommendations,
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
