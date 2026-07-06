"""Modernize ZIP 생성 — `generate_modernize_zip()`.

기존 `app/engine/generator.py.generate_all()` 와 완전히 분리. 로컬에서 즉시 실행 가능한
현대화 팩(R1)을 생성한다:

    project-root/
    ├── .clickeye/linear-issues.json      # 등록된 이슈 매핑 (중복 등록 방지)
    ├── .ralph/tasks/<identifier>.md      # rec.prompt_md → AI 작업 지시
    ├── docs/diagnosis.md                 # CodebaseAnalysis.llm_summary_md
    ├── docs/diagnosis.json               # 분석 결과 머신리더블
    ├── docs/modernize/                   # 6단계 Phase 산출물 (requirements/tobe/plan/preflight)
    │   ├── requirements.md
    │   ├── tobe-architecture.md
    │   ├── modernization-plan.md
    │   ├── preflight-review.md
    │   └── plan.json
    ├── .claude/
    │   ├── CLAUDE.md                     # 현대화 룰: 단계 게이트/커밋 규칙/기록지침/롤백 원칙
    │   ├── agents/                       # modernize-pm 외 5개 역할 에이전트
    │   └── skills/                       # modernize-phase-runner / migration-verify / record-work
    ├── MODERNIZE_README.md               # 1-pager 실행 가이드
    └── .env.example                      # LINEAR_API_KEY/TEAM_ID/REPO_URL 안내

`platform_id`는 위저드의 플랫폼 선택과 동일한 축이나, 현재는 `.claude/` 산출만 구현한다.
`.gemini/`/`.cursor/` 변환은 `_agent_dir_prefix()` 에 후속 마일스톤에서 분기를 추가한다.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any


def _agent_dir_prefix(platform_id: str) -> str:
    """플랫폼별 에이전트 디렉토리 접두사.

    위저드 platform 선택과 동일한 축(claude-code/gemini-cli/cursor)이나,
    `.gemini/`/`.cursor/` 변환은 아직 미구현 — 항상 `.claude/` 로 폴백한다.
    """
    return ".claude"


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
bash scripts/auto_dev_pipeline.sh   # (별도 ClickEye 솔루션 ZIP 의 스크립트 활용)
```

## 4. 결과 확인
- 각 이슈는 `fix/{scenario}/<slug>` 브랜치로 PR 생성
- `harness-gate.sh` (lint/type/test) 통과 시 자동 라벨 `qa-ready`

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

_CLAUDE_MD_TEMPLATE = """# {project_name} — Modernize 현대화 룰

> GitHub: `{repo_full_name}` | 시나리오: **{scenario}** | 세션: `{session_id}`

## 단계 게이트 (6단계)
`asis → requirements → tobe → plan → preflight → execute` 순서로 진행하며,
**앞 단계 산출물이 사용자 승인(approved) 되기 전에는 다음 단계로 넘어가지 않는다.**
각 단계 산출물은 `docs/modernize/`에 있다.

| 단계 | 산출물 | 담당 에이전트 |
|------|--------|---------------|
| asis | `docs/diagnosis.md` | `asis-analyzer` |
| requirements | `docs/modernize/requirements.md` | `asis-analyzer` |
| tobe | `docs/modernize/tobe-architecture.md` | `modernize-pm` |
| plan | `docs/modernize/modernization-plan.md`, `plan.json` | `modernize-pm` |
| preflight | `docs/modernize/preflight-review.md` | `test-guardian` |
| execute | 코드/DB 변경 | `code-migrator`, `db-migrator` |

## 커밋 규칙
- 커밋 메시지는 한국어, `[phase] 작업 내용` 형식 (예: `[execute] Python 3.8 → 3.12 업그레이드`)
- 한 커밋 = 한 논리적 변경. `.ralph/tasks/<identifier>.md` 단위로 커밋 분리
- 커밋 전 반드시 lint/typecheck/test 통과 (`test-guardian` 게이트)

## 기록 지침
- 각 단계 완료 시 `work-recorder`가 `.ralph/tasks/<identifier>.md`에 진행 로그를 남긴다
- Linear 이슈가 있으면(`.clickeye/linear-issues.json`) 상태를 동기화한다

## 롤백 원칙
- 각 단계는 git 커밋 단위로 되돌릴 수 있어야 한다 (`git revert`, 강제 push 금지)
- DB 마이그레이션은 반드시 downgrade 경로를 확인한 뒤 적용한다 (`db-migrator` 책임)
- execute 단계에서 회귀가 발생하면 직전 승인된 단계로 롤백 후 재계획한다
"""

_AGENT_TEMPLATES: dict[str, str] = {
    "modernize-pm": """---
name: modernize-pm
description: 6단계 워크플로를 조율하는 PM 에이전트. 단계 게이트를 지키며 하위 에이전트에 위임한다.
---

# modernize-pm

> 대상: `{repo_full_name}` ({scenario}) | 세션: `{session_id}`

## 역할
6단계 워크플로(asis/requirements/tobe/plan/preflight/execute)의 진행을 조율하는 PM 에이전트.
각 단계 산출물을 검토하고, 사용자 승인 없이는 다음 단계로 진행하지 않는다.

## 책임
- 단계 게이트 유지: `docs/modernize/` 산출물이 승인되었는지 확인
- 하위 에이전트(`asis-analyzer`, `code-migrator`, `db-migrator`, `test-guardian`)에 작업 위임
- `work-recorder`를 통해 진행 상황을 기록

## 참조
- `.claude/CLAUDE.md` — 단계 게이트/커밋/롤백 원칙
""",
    "asis-analyzer": """---
name: asis-analyzer
description: As-Is 코드베이스를 분석해 요구사항/목표 아키텍처 산출물을 작성하는 에이전트.
---

# asis-analyzer

> 대상: `{repo_full_name}` ({scenario}) | 세션: `{session_id}`

## 역할
현재(As-Is) 코드베이스의 스택·의존성·리스크를 분석하고, 목표(To-Be) 스택과의 격차를 정리한다.

## 책임
- `docs/diagnosis.md`/`docs/diagnosis.json`을 바탕으로 `docs/modernize/requirements.md` 작성/보강
- `docs/modernize/tobe-architecture.md`에 목표 스택 제안
- 스택 버전, 프레임워크, 인프라 종속성을 구조화하여 기록

## 참조
- `.claude/CLAUDE.md`
""",
    "code-migrator": """---
name: code-migrator
description: execute 단계에서 계획에 따라 애플리케이션 코드를 이관하는 에이전트.
---

# code-migrator

> 대상: `{repo_full_name}` ({scenario}) | 세션: `{session_id}`

## 역할
`docs/modernize/modernization-plan.md`(및 `.ralph/tasks/*.md`)에 따라 애플리케이션 코드를 이관한다.

## 책임
- execute 단계에서만 활동 (preflight 승인 이후)
- `.ralph/tasks/<identifier>.md` 단위로 작업, 완료 시 `test-guardian` 게이트 통과 필수
- 코드 변경은 항상 작은 단위 커밋으로 분리

## 참조
- `.claude/CLAUDE.md`
""",
    "db-migrator": """---
name: db-migrator
description: DB 마이그레이션 담당 에이전트. downgrade 경로를 반드시 확인한다.
---

# db-migrator

> 대상: `{repo_full_name}` ({scenario}) | 세션: `{session_id}`

## 역할
DB 스키마/버전 마이그레이션을 담당한다 (예: Alembic, 벤더 마이그레이션 도구).

## 책임
- 마이그레이션 적용 전 downgrade 경로 확인 (롤백 원칙 준수)
- `docs/modernize/modernization-plan.md`의 DB 관련 항목만 처리
- 데이터 손실 위험이 있는 변경은 `modernize-pm` 승인 필수

## 참조
- `.claude/CLAUDE.md`
""",
    "test-guardian": """---
name: test-guardian
description: lint/typecheck/test 게이트로 회귀를 방지하는 QA 에이전트.
---

# test-guardian

> 대상: `{repo_full_name}` ({scenario}) | 세션: `{session_id}`

## 역할
lint/typecheck/test 게이트를 지켜 회귀를 방지하는 QA 에이전트.

## 책임
- preflight 단계: 기존 테스트 스위트가 통과하는지 기준선 확인 → `docs/modernize/preflight-review.md`
- execute 단계: 각 커밋 전 lint/typecheck/test 실행, 실패 시 커밋 차단
- 회귀 발견 시 `modernize-pm`에 보고, 직전 승인 단계로 롤백 제안

## 참조
- `.claude/CLAUDE.md`
""",
    "work-recorder": """---
name: work-recorder
description: 작업 진행 상황과 Linear 이슈 상태를 기록/동기화하는 에이전트.
---

# work-recorder

> 대상: `{repo_full_name}` ({scenario}) | 세션: `{session_id}`

## 역할
각 단계/작업의 진행 상황을 기록하고, Linear 이슈 상태를 동기화한다.

## 책임
- `.ralph/tasks/<identifier>.md`에 진행 로그(시각/상태/비고) 추가
- `.clickeye/linear-issues.json`에 매핑된 이슈가 있으면 상태 동기화 안내
- 단계 전환 시 `docs/modernize/`에 승인 시각 기록

## 참조
- `.claude/CLAUDE.md`
""",
}

_SKILL_TEMPLATES: dict[str, str] = {
    "modernize-phase-runner": """---
name: modernize-phase-runner
description: 6단계 워크플로를 순서대로 실행한다. 현재 단계 파악 및 전환에 사용.
user-invocable: true
---

# modernize-phase-runner

6단계 워크플로(asis/requirements/tobe/plan/preflight/execute)를 순서대로 실행한다.
현재 단계는 `docs/modernize/`에 존재하는 산출물로 판단하며, 각 단계 산출물이
승인되지 않으면 다음 단계로 진행하지 않는다.

## 사용 시점
- 세션 시작 시 현재 단계 파악
- 각 단계 산출물 작성/보강 후 다음 단계로 전환할 때
""",
    "migration-verify": """---
name: migration-verify
description: lint/typecheck/test로 마이그레이션 변경의 회귀 여부를 검증한다.
user-invocable: true
---

# migration-verify

lint/typecheck/test를 실행하여 마이그레이션 변경이 기존 기능을 깨뜨리지 않았는지 검증한다.

## 사용 시점
- execute 단계에서 커밋 전
- preflight 단계에서 기준선(baseline) 확인 시
""",
    "record-work": """---
name: record-work
description: 작업 완료 후 진행 상황과 Linear 이슈를 기록한다.
user-invocable: true
---

# record-work

작업 완료 후 `.ralph/tasks/<identifier>.md`와 Linear 이슈에 진행 상황을 기록한다.

## 사용 시점
- 각 단계/작업 완료 직후 (유의미한 코드 변경 포함)
""",
}

_PHASE_DOC_SPECS: list[tuple[str, str, str]] = [
    (
        "requirements",
        "requirements",
        "# 요구사항 (Requirements)\n\n(아직 승인된 요구사항 산출물이 없습니다.)\n",
    ),
    (
        "tobe",
        "tobe-architecture",
        "# 목표 아키텍처 (To-Be)\n\n(아직 승인된 목표 아키텍처 산출물이 없습니다.)\n",
    ),
    (
        "plan",
        "modernization-plan",
        "# 마이그레이션 계획 (Plan)\n\n(아직 승인된 계획 산출물이 없습니다.)\n",
    ),
    (
        "preflight",
        "preflight-review",
        "# 사전 점검 (Preflight)\n\n(아직 승인된 사전 점검 산출물이 없습니다.)\n",
    ),
]


def _pick_phase_content_md(phase_artifacts: list[dict[str, Any]], phase: str, fallback: str) -> str:
    for artifact in phase_artifacts:
        if artifact.get("phase") == phase and artifact.get("content_md"):
            return str(artifact["content_md"])
    return fallback


def _pick_phase_content_json(phase_artifacts: list[dict[str, Any]], phase: str) -> dict[str, Any]:
    for artifact in phase_artifacts:
        if artifact.get("phase") == phase and artifact.get("content_json"):
            content = artifact["content_json"]
            return content if isinstance(content, dict) else {"value": content}
    return {}


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
    phase_artifacts: list[dict[str, Any]] | None = None,
    platform_id: str = "claude-code",
) -> bytes:
    """ZIP 바이트 반환. 호출자가 file response 로 streaming."""
    project_name = project_name or repo_full_name.split("/")[-1] or "modernize-project"
    linear_issues = linear_issues or []
    phase_artifacts = phase_artifacts or []
    agent_dir = _agent_dir_prefix(platform_id)
    agent_ctx = {
        "project_name": project_name,
        "repo_full_name": repo_full_name,
        "scenario": scenario,
        "session_id": session_id,
    }

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

        # 7) docs/modernize/ — 6단계 Phase 산출물 (승인분 없으면 폴백 플레이스홀더)
        plan_json: dict[str, Any] = {}
        for phase, doc_slug, fallback in _PHASE_DOC_SPECS:
            content_md = _pick_phase_content_md(phase_artifacts, phase, fallback)
            zf.writestr(f"docs/modernize/{doc_slug}.md", content_md)
            if phase == "plan":
                plan_json = _pick_phase_content_json(phase_artifacts, phase)
        zf.writestr(
            "docs/modernize/plan.json",
            json.dumps(plan_json, ensure_ascii=False, indent=2, default=str),
        )

        # 8) .claude/CLAUDE.md — 현대화 룰
        zf.writestr(f"{agent_dir}/CLAUDE.md", _CLAUDE_MD_TEMPLATE.format(**agent_ctx))

        # 9) .claude/agents/*.md — 역할별 에이전트
        for slug, template in _AGENT_TEMPLATES.items():
            zf.writestr(f"{agent_dir}/agents/{slug}.md", template.format(**agent_ctx))

        # 10) .claude/skills/<slug>/SKILL.md
        for slug, content in _SKILL_TEMPLATES.items():
            zf.writestr(f"{agent_dir}/skills/{slug}/SKILL.md", content)

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
