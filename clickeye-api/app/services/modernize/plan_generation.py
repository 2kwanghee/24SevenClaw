"""Phase 4 — plan 산출물 생성.

`tobe` phase 산출물이 승인된 이후에만 호출 가능. 세션의 권장안(전체, idx 순)을 읽어
저장된 depends_on 이 위상정렬 가능한지 재검증하고 `plan.json`(CE-290 오케스트레이터
입력) / `modernization-plan.md` 를 `modernize_phase_artifacts` 에 upsert 한다.
내용이 바뀌면 재검수를 강제하기 위해 매번 `approved_at` 을 초기화한다.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modernize_phase_artifact import ModernizePhaseArtifact
from app.models.modernize_recommendation import ModernizeRecommendation
from app.models.modernize_session import ModernizeSession
from app.services.modernize import plan_builder

PLAN_JSON_ARTIFACT_TYPE = "plan_json"
PLAN_SUMMARY_ARTIFACT_TYPE = "plan_summary"


class TobeNotApprovedError(Exception):
    """tobe phase 산출물이 아직 승인되지 않아 plan 생성을 진행할 수 없음."""


class NoRecommendationsError(Exception):
    """세션에 권장안이 없어 plan 을 생성할 수 없음."""


async def is_tobe_approved(db: AsyncSession, session_id: UUID) -> bool:
    result = await db.execute(
        select(ModernizePhaseArtifact.id).where(
            ModernizePhaseArtifact.session_id == session_id,
            ModernizePhaseArtifact.phase == "tobe",
            ModernizePhaseArtifact.approved_at.is_not(None),
        )
    )
    return result.scalar_one_or_none() is not None


async def generate_plan_artifacts(
    db: AsyncSession,
    session_row: ModernizeSession,
) -> tuple[ModernizePhaseArtifact, ModernizePhaseArtifact]:
    """plan.json + modernization-plan.md 생성/갱신 + current_phase='plan' 전이."""
    session_id: UUID = session_row.id  # type: ignore[assignment]

    if not await is_tobe_approved(db, session_id):
        raise TobeNotApprovedError("tobe 단계 산출물이 아직 승인되지 않았습니다.")

    recs_result = await db.execute(
        select(ModernizeRecommendation)
        .where(ModernizeRecommendation.session_id == session_id)
        .order_by(ModernizeRecommendation.idx.asc())
    )
    rec_rows = list(recs_result.scalars().all())
    if not rec_rows:
        raise NoRecommendationsError("세션에 권장안이 없어 계획을 생성할 수 없습니다.")

    rec_dicts: list[dict[str, Any]] = [
        {
            "id": str(row.id),
            "idx": row.idx,
            "title": row.title,
            "category": row.category,
            "effort": row.effort,
            "risk": row.risk,
            "assigned_agent": row.assigned_agent,
            "depends_on": row.depends_on or [],
            "wave": row.wave,
        }
        for row in rec_rows
    ]

    # DAG 재검증 — 저장된 depends_on 이 위상정렬 가능한지 확인 (사이클이면 예외)
    plan_builder.compute_waves([r["depends_on"] for r in rec_dicts])

    plan_json = plan_builder.build_plan_json(session_id=str(session_id), recs=rec_dicts)
    plan_md = plan_builder.render_plan_markdown(rec_dicts)

    json_artifact = await _upsert_plan_artifact(
        db,
        session_id=session_id,
        artifact_type=PLAN_JSON_ARTIFACT_TYPE,
        content_json=plan_json,
        content_md=None,
    )
    summary_artifact = await _upsert_plan_artifact(
        db,
        session_id=session_id,
        artifact_type=PLAN_SUMMARY_ARTIFACT_TYPE,
        content_json=None,
        content_md=plan_md,
    )

    session_row.current_phase = "plan"  # type: ignore[assignment]
    await db.commit()
    await db.refresh(json_artifact)
    await db.refresh(summary_artifact)
    return json_artifact, summary_artifact


async def _upsert_plan_artifact(
    db: AsyncSession,
    *,
    session_id: UUID,
    artifact_type: str,
    content_json: dict[str, Any] | None,
    content_md: str | None,
) -> ModernizePhaseArtifact:
    result = await db.execute(
        select(ModernizePhaseArtifact).where(
            ModernizePhaseArtifact.session_id == session_id,
            ModernizePhaseArtifact.phase == "plan",
            ModernizePhaseArtifact.artifact_type == artifact_type,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = ModernizePhaseArtifact(
            session_id=session_id,
            phase="plan",
            artifact_type=artifact_type,
        )
        db.add(row)
    row.content_json = content_json  # type: ignore[assignment]
    row.content_md = content_md  # type: ignore[assignment]
    # 내용 갱신 시 재검수 필요 — approved_at 초기화
    row.approved_at = None  # type: ignore[assignment]
    return row
