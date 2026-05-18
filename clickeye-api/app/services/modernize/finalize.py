"""Finalize 흐름 — Linear 등록 + ZIP 빌드 + 세션 상태 갱신.

`POST /modernize/sessions/{id}/finalize` 가 호출. idempotency 는 단순화: 동일 세션에
finalize 가 이미 호출됐다면 (status='finalized') 기존 Linear 매핑 그대로 반환.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.models.codebase_analysis import CodebaseAnalysis
from app.models.modernize_recommendation import ModernizeRecommendation
from app.models.modernize_session import ModernizeSession
from app.models.project_linear_credentials import ProjectLinearCredentials
from app.models.user_linear_credentials import UserLinearCredentials
from app.services import linear_service


async def resolve_linear_credentials(
    db: AsyncSession,
    user_id: UUID,
    *,
    project_id: UUID | None = None,
) -> tuple[str, str] | None:
    """Linear API key + team_id 자격증명 조회.

    project_id 가 있으면 ProjectLinearCredentials 우선 → 없으면 UserLinearCredentials.
    """
    if project_id is not None:
        result = await db.execute(
            select(ProjectLinearCredentials).where(
                ProjectLinearCredentials.project_id == project_id
            )
        )
        proj_creds = result.scalar_one_or_none()
        if proj_creds is not None:
            try:
                api_key = decrypt(str(proj_creds.encrypted_api_key))
                return api_key, str(proj_creds.team_id)
            except Exception:
                pass

    result = await db.execute(
        select(UserLinearCredentials).where(UserLinearCredentials.user_id == user_id)
    )
    user_creds = result.scalar_one_or_none()
    if user_creds is None:
        return None
    try:
        api_key = decrypt(str(user_creds.encrypted_api_key))
        return api_key, str(user_creds.team_id)
    except Exception:
        return None


async def register_linear_issues(
    db: AsyncSession,
    *,
    session_row: ModernizeSession,
    analysis: CodebaseAnalysis | None,
    selected_recs: list[ModernizeRecommendation],
    api_key: str,
    team_id: str,
) -> dict[str, Any]:
    """parent + child 이슈 일괄 등록. 각 rec 의 linear_issue_id/identifier 채움.

    Returns:
        {parent_url, parent_identifier, child_count, errors: [...]}
    """
    summary_md = (analysis.llm_summary_md if analysis is not None else "") or ""
    parent = linear_service.create_modernize_parent_issue(
        api_key,
        team_id,
        repo_full_name=str(session_row.repo_full_name),
        scenario=str(session_row.scenario),
        summary_md=str(summary_md),
    )

    rec_payloads = [
        {
            "id": str(rec.id),
            "title": str(rec.title),
            "rationale_md": rec.rationale_md,
            "prompt_md": rec.prompt_md,
            "risk": str(rec.risk),
            "effort": str(rec.effort),
            "priority": rec.priority,
        }
        for rec in selected_recs
    ]
    children = linear_service.create_modernize_child_issues(
        api_key,
        team_id,
        rec_payloads,
        parent_id=parent.get("id") or None,
    )

    # rec → linear 매핑 영속
    errors: list[str] = []
    by_rec_id = {c.get("rec_id"): c for c in children if c.get("rec_id")}
    for rec in selected_recs:
        ch = by_rec_id.get(str(rec.id))
        if ch is None or "error" in ch:
            errors.append(str(rec.id))
            continue
        rec.linear_issue_id = ch.get("issue_id")  # type: ignore[assignment]
        rec.linear_identifier = ch.get("identifier")  # type: ignore[assignment]
    await db.commit()

    return {
        "parent_url": parent.get("url", ""),
        "parent_identifier": parent.get("identifier", ""),
        "child_count": sum(1 for c in children if "error" not in c),
        "errors": errors,
    }


async def mark_finalized(
    db: AsyncSession,
    session_id: UUID,
) -> None:
    """ModernizeSession.status = 'finalized'."""
    result = await db.execute(select(ModernizeSession).where(ModernizeSession.id == session_id))
    row = result.scalar_one_or_none()
    if row is None:
        return
    row.status = "finalized"  # type: ignore[assignment]
    row.progress_pct = 100  # type: ignore[assignment]
    row.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    await db.commit()
