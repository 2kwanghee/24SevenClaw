"""Phase 3 — To-Be 아키텍처 설계 산출물 생성.

requirements(Phase 2) 승인 산출물 + as-is 분석(Phase 1, `CodebaseAnalysis`)을 입력으로
목표 아키텍처 설계 문서(`tobe-architecture.md`)와 갭 매트릭스(`gap-matrix.json`)를 생성한다.

recommendations.py 와 동일한 패턴: strict JSON 요청 + 1회 재시도 + Anthropic key 미설정 시
deterministic fallback. 복잡도(≥0.7)가 높은 세션은 `anthropic_model_advanced`(Opus) 로 격상한다.
"""

from __future__ import annotations

import json
import re
from typing import Any, cast
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.codebase_analysis import CodebaseAnalysis
from app.models.modernize_phase_artifact import ModernizePhaseArtifact
from app.models.modernize_session import ModernizeSession
from app.schemas.modernize import RequirementsArtifactContent, StackDescriptor
from app.services.claude_service import ClaudeService

_TOBE_SYSTEM = """You are a senior solutions architect producing a target architecture design.

Input (JSON): scenario, goals_text, as_is (lang_distribution, framework_signals,
outdated_packages, risk_flags, dep_graph_mermaid),
requirements (as_is_stack, to_be_stack, notes_md).

Your task: produce STRICT JSON only — no prose, no markdown fences outside the JSON itself.

Output schema:
{
  "tobe_architecture_md": "<markdown design doc covering: 1) 목표 스택 구성, 2) 계층 구조,
     3) a ```mermaid fenced block comparing as-is and to-be architecture,
     4) 랜딩존(디렉토리/인프라 구성)>",
  "gap_matrix": [
    {
      "area": "code" | "dependency" | "database" | "infra" | "test",
      "as_is": "<current state, one line>",
      "to_be": "<target state, one line>",
      "transition_type": "rehost" | "replatform" | "refactor"
    },
    ...
  ]
}

Rules:
- Cover all 5 areas (code, dependency, database, infra, test) at least once when data supports it.
- Korean preferred for tobe_architecture_md / as_is / to_be text when goals_text is Korean.
"""


async def generate_tobe_architecture(
    *,
    scenario: str,
    goals_text: str,
    as_is_stack: dict[str, Any],
    to_be_stack: dict[str, Any],
    requirements_notes_md: str | None,
    lang_distribution: dict[str, float],
    framework_signals: dict[str, Any],
    outdated_packages: list[dict[str, Any]],
    risk_flags: list[str],
    dep_graph: dict[str, Any] | None,
    llm_summary: str,
) -> tuple[str, list[dict[str, Any]], int]:
    """(tobe_architecture_md, gap_matrix, tokens_used) 반환.

    Anthropic key 미설정 또는 LLM 실패 시 정적 갭 매트릭스(outdated/risk_flags 기반)로 폴백.
    """
    if not settings.anthropic_api_key:
        return (
            _deterministic_tobe_md(
                scenario=scenario,
                as_is_stack=as_is_stack,
                to_be_stack=to_be_stack,
                dep_graph=dep_graph,
            ),
            _deterministic_gap_matrix(
                as_is_stack=as_is_stack,
                to_be_stack=to_be_stack,
                outdated_packages=outdated_packages,
                risk_flags=risk_flags,
                requirements_notes_md=requirements_notes_md,
            ),
            0,
        )

    context = {
        "scenario": scenario,
        "goals_text": goals_text,
        "as_is": {
            "lang_distribution": lang_distribution,
            "framework_signals": framework_signals,
            "outdated_packages": outdated_packages[:30],
            "risk_flags": risk_flags,
            "dep_graph_mermaid": (dep_graph or {}).get("mermaid", ""),
        },
        "requirements": {
            "as_is_stack": as_is_stack,
            "to_be_stack": to_be_stack,
            "notes_md": requirements_notes_md or "",
        },
        "llm_summary": llm_summary[:4000],
    }

    model = _select_model(
        outdated_packages=outdated_packages, risk_flags=risk_flags, scenario=scenario
    )

    parsed = await _call_claude(model=model, context=context)
    if parsed is None:
        parsed = await _call_claude(model=model, context=context, retry=True)

    if parsed is None:
        return (
            _deterministic_tobe_md(
                scenario=scenario,
                as_is_stack=as_is_stack,
                to_be_stack=to_be_stack,
                dep_graph=dep_graph,
            ),
            _deterministic_gap_matrix(
                as_is_stack=as_is_stack,
                to_be_stack=to_be_stack,
                outdated_packages=outdated_packages,
                risk_flags=risk_flags,
                requirements_notes_md=requirements_notes_md,
            ),
            0,
        )

    tobe_md, gap_matrix, tokens_used = parsed
    return tobe_md, gap_matrix, tokens_used


def _estimate_complexity(
    *,
    outdated_packages: list[dict[str, Any]],
    risk_flags: list[str],
    scenario: str,
) -> float:
    """0.0~1.0 복잡도 휴리스틱. deep-thinker 위임 규칙(≥0.7 시 Opus)과 동일 임계값 사용."""
    score = 0.0
    score += min(len(outdated_packages) / 20, 0.4)
    score += min(len(risk_flags) / 5, 0.3)
    if scenario == "language_migrate":
        score += 0.3
    elif scenario == "refactor":
        score += 0.1
    return min(score, 1.0)


def _select_model(
    *, outdated_packages: list[dict[str, Any]], risk_flags: list[str], scenario: str
) -> str:
    complexity = _estimate_complexity(
        outdated_packages=outdated_packages, risk_flags=risk_flags, scenario=scenario
    )
    if complexity >= 0.7:
        return settings.anthropic_model_advanced
    return settings.anthropic_model_default


async def _call_claude(
    *, model: str, context: dict[str, Any], retry: bool = False
) -> tuple[str, list[dict[str, Any]], int] | None:
    service = ClaudeService()
    client = service._get_client()  # noqa: SLF001
    try:
        response = await client.messages.create(
            model=model,
            max_tokens=4000 if not retry else 3000,
            system=_TOBE_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False, indent=2),
                }
            ],
        )
    except Exception:
        return None

    raw = ""
    for block in response.content:
        if hasattr(block, "text"):
            raw += block.text

    parsed = _parse_strict_tobe(raw)
    if parsed is None:
        return None
    tobe_md, gap_matrix = parsed
    tokens_used = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
    return tobe_md, gap_matrix, tokens_used


def _parse_strict_tobe(raw: str) -> tuple[str, list[dict[str, Any]]] | None:
    if not raw.strip():
        return None
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```\s*$", "", raw.strip(), flags=re.MULTILINE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    tobe_md = data.get("tobe_architecture_md")
    if not isinstance(tobe_md, str) or not tobe_md.strip():
        return None

    raw_matrix = data.get("gap_matrix")
    gap_matrix: list[dict[str, Any]] = []
    if isinstance(raw_matrix, list):
        for row in raw_matrix:
            if not isinstance(row, dict):
                continue
            area = row.get("area")
            as_is = row.get("as_is")
            to_be = row.get("to_be")
            if not (isinstance(area, str) and isinstance(as_is, str) and isinstance(to_be, str)):
                continue
            gap_matrix.append(
                {
                    "area": _normalize_area(area),
                    "as_is": as_is,
                    "to_be": to_be,
                    "transition_type": _normalize_transition(row.get("transition_type")),
                }
            )
    return tobe_md, gap_matrix


def _normalize_area(v: str) -> str:
    return v if v in ("code", "dependency", "database", "infra", "test") else "code"


def _normalize_transition(v: object) -> str:
    if isinstance(v, str) and v in ("rehost", "replatform", "refactor"):
        return v
    return "refactor"


def _deterministic_tobe_md(
    *,
    scenario: str,
    as_is_stack: dict[str, Any],
    to_be_stack: dict[str, Any],
    dep_graph: dict[str, Any] | None,
) -> str:
    """LLM 미사용 시 정적 To-Be 아키텍처 문서 — 분석 데이터 + 스택 비교만으로 생성."""
    mermaid = (dep_graph or {}).get("mermaid") or "graph TD\n  as_is[As-Is]\n  to_be[To-Be]"
    lines = [
        "# To-Be 아키텍처 설계 (placeholder)",
        "",
        f"> 시나리오: **{scenario}**",
        "",
        "## 1. 목표 스택 구성",
        f"- DB: `{as_is_stack.get('db_type', '-')}"
        f" {as_is_stack.get('db_version', '')}` → `{to_be_stack.get('db_type', '-')}"
        f" {to_be_stack.get('db_version', '')}`",
        f"- Runtime: `{as_is_stack.get('runtime', '-')}"
        f" {as_is_stack.get('runtime_version', '')}` → `{to_be_stack.get('runtime', '-')}"
        f" {to_be_stack.get('runtime_version', '')}`",
        f"- Framework: `{as_is_stack.get('framework', '-')}"
        f" {as_is_stack.get('framework_version', '')}` → `{to_be_stack.get('framework', '-')}"
        f" {to_be_stack.get('framework_version', '')}`",
        f"- Infra: `{as_is_stack.get('infra', '-')}` → `{to_be_stack.get('infra', '-')}`",
        "",
        "## 2. 계층 구조",
        "이 요약은 Anthropic API key 미설정 시 표시되는 정적 문서입니다. "
        "key 설정 후 재생성 시 계층별 상세 구조가 채워집니다.",
        "",
        "## 3. As-Is ↔ To-Be 다이어그램",
        "```mermaid",
        mermaid,
        "```",
        "",
        "## 4. 랜딩존 (디렉토리/인프라 구성)",
        "- 세부 랜딩존 구성은 LLM 재생성 후 제공됩니다.",
    ]
    return "\n".join(lines)


def _deterministic_gap_matrix(
    *,
    as_is_stack: dict[str, Any],
    to_be_stack: dict[str, Any],
    outdated_packages: list[dict[str, Any]],
    risk_flags: list[str],
    requirements_notes_md: str | None,
) -> list[dict[str, Any]]:
    """LLM 미사용 시 정적 갭 매트릭스 — outdated/risk_flags/스택 diff 로만 구성."""
    rows: list[dict[str, Any]] = []

    for pkg in outdated_packages[:10]:
        name = pkg.get("name") or "package"
        current = pkg.get("current") or ""
        latest = pkg.get("latest") or ""
        severity = pkg.get("severity") or "low"
        rows.append(
            {
                "area": "dependency",
                "as_is": f"{name} {current}",
                "to_be": f"{name} {latest}",
                "transition_type": "replatform" if severity == "high" else "refactor",
            }
        )

    for flag in risk_flags[:10]:
        rows.append(
            {
                "area": "infra",
                "as_is": flag,
                "to_be": f"{flag} 해소",
                "transition_type": "replatform",
            }
        )

    if as_is_stack.get("db_type") or to_be_stack.get("db_type"):
        as_is_db = f"{as_is_stack.get('db_type', '-')} {as_is_stack.get('db_version', '')}".strip()
        to_be_db = f"{to_be_stack.get('db_type', '-')} {to_be_stack.get('db_version', '')}".strip()
        if as_is_db != to_be_db:
            rows.append(
                {
                    "area": "database",
                    "as_is": as_is_db,
                    "to_be": to_be_db,
                    "transition_type": "rehost",
                }
            )

    if requirements_notes_md:
        rows.append(
            {
                "area": "code",
                "as_is": "requirements 단계 검토 노트 미반영 상태",
                "to_be": requirements_notes_md[:200],
                "transition_type": "refactor",
            }
        )

    rows.append(
        {
            "area": "test",
            "as_is": "전환 대상 코드에 대한 회귀 테스트 커버리지 미확인",
            "to_be": "전환 단위별 회귀 테스트 추가 및 CI 게이트 반영",
            "transition_type": "refactor",
        }
    )

    return rows


def _parse_requirements_content(content_json: dict[str, Any] | None) -> RequirementsArtifactContent:
    if isinstance(content_json, dict):
        try:
            return RequirementsArtifactContent.model_validate(content_json)
        except ValidationError:
            pass
    return RequirementsArtifactContent(as_is_stack=StackDescriptor(), to_be_stack=StackDescriptor())


async def generate_and_persist_tobe_artifacts(
    db: AsyncSession,
    *,
    session_row: ModernizeSession,
    requirements_artifact: ModernizePhaseArtifact,
) -> list[ModernizePhaseArtifact]:
    """requirements 산출물 승인 후 tobe phase 산출물(문서 + 갭 매트릭스) 생성 + 영속.

    반환된 두 행은 각각 `artifact_type='tobe_architecture'`(content_md) 와
    `artifact_type='gap_matrix'`(content_json) 이다.
    """
    session_id = cast(UUID, session_row.id)

    analysis_result = await db.execute(
        select(CodebaseAnalysis).where(CodebaseAnalysis.session_id == session_id)
    )
    analysis = analysis_result.scalar_one_or_none()

    req_content_json = cast("dict[str, Any] | None", requirements_artifact.content_json)
    req_content = _parse_requirements_content(req_content_json)

    lang_distribution = cast(
        "dict[str, float]", analysis.lang_distribution if analysis else {}
    )
    framework_signals = cast(
        "dict[str, Any]", analysis.framework_signals if analysis else {}
    )
    outdated_packages = cast(
        "list[dict[str, Any]]", analysis.outdated_packages if analysis else []
    )
    risk_flags = cast("list[str]", analysis.risk_flags if analysis else [])
    dep_graph = cast("dict[str, Any] | None", analysis.dep_graph if analysis else None)
    llm_summary = str(analysis.llm_summary_md if analysis and analysis.llm_summary_md else "")

    tobe_md, gap_matrix, tokens_used = await generate_tobe_architecture(
        scenario=str(session_row.scenario),
        goals_text=str(session_row.goals_text or ""),
        as_is_stack=req_content.as_is_stack.model_dump(),
        to_be_stack=req_content.to_be_stack.model_dump(),
        requirements_notes_md=req_content.notes_md,
        lang_distribution=lang_distribution or {},
        framework_signals=framework_signals or {},
        outdated_packages=outdated_packages or [],
        risk_flags=risk_flags or [],
        dep_graph=dep_graph,
        llm_summary=llm_summary,
    )

    tobe_artifact = ModernizePhaseArtifact(
        session_id=session_id,
        phase="tobe",
        artifact_type="tobe_architecture",
        content_md=tobe_md,
    )
    gap_artifact = ModernizePhaseArtifact(
        session_id=session_id,
        phase="tobe",
        artifact_type="gap_matrix",
        content_json={"gap_matrix": gap_matrix, "tokens_used": tokens_used},
    )
    db.add(tobe_artifact)
    db.add(gap_artifact)
    await db.commit()
    await db.refresh(tobe_artifact)
    await db.refresh(gap_artifact)
    return [tobe_artifact, gap_artifact]
