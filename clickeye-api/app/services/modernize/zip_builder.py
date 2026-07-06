"""Modernize ZIP 생성 — `generate_modernize_zip()`.

기존 `app/engine/generator.py.generate_all()` 와 완전히 분리. Modernize 만의 최소 산출:

    project-root/
    ├── .clickeye/linear-issues.json      # 등록된 이슈 매핑 (중복 등록 방지)
    ├── .ralph/tasks/<identifier>.md      # rec.prompt_md → AI 작업 지시
    ├── docs/diagnosis.md                 # CodebaseAnalysis.llm_summary_md
    ├── docs/diagnosis.json               # 분석 결과 머신리더블
    ├── docs/preflight-review.md          # Pre-flight 체크리스트 승인본 (있을 때만)
    ├── MODERNIZE_README.md               # 1-pager 실행 가이드
    └── .env.example                      # LINEAR_API_KEY/TEAM_ID/REPO_URL 안내

기존 자산(`auto_dev_pipeline.sh` 등) 통합은 M7-B 또는 후속 마일스톤에서.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any

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
    preflight_review_md: str | None = None,
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

        # 7) docs/preflight-review.md — Pre-flight 게이트 승인 시 로컬 재확인용 (선택)
        if preflight_review_md:
            zf.writestr("docs/preflight-review.md", preflight_review_md)

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
