"""plan phase 산출물 생성 + diff-merge upsert 단위 테스트 (Phase 4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modernize_phase_artifact import ModernizePhaseArtifact
from app.models.modernize_recommendation import ModernizeRecommendation
from app.models.modernize_session import ModernizeSession
from app.models.user import User
from app.services.modernize import plan_generation
from app.services.modernize.pipeline import _upsert_recommendations


async def _make_session(db: AsyncSession) -> ModernizeSession:
    user = User(email=f"{uuid.uuid4()}@example.com", display_name="Tester")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    session_row = ModernizeSession(
        user_id=user.id,
        repo_full_name="acme/widgets",
        scenario="versionup",
        status="ready",
    )
    db.add(session_row)
    await db.commit()
    await db.refresh(session_row)
    return session_row


def _rec_dict(category: str, title: str, target_path: str | None = None) -> dict:
    return {
        "category": category,
        "target_path": target_path,
        "before": None,
        "after": None,
        "title": title,
        "rationale_md": None,
        "effort": "M",
        "risk": "med",
        "priority": 50,
        "prompt_md": None,
    }


@pytest.mark.asyncio
async def test_upsert_recommendations_computes_plan_fields(db_session: AsyncSession) -> None:
    session_row = await _make_session(db_session)
    recs = [
        _rec_dict("migrate", "schema", target_path="clickeye-api/schema.sql"),
        _rec_dict("refactor", "app code", target_path="clickeye-api/app/main.py"),
    ]

    await _upsert_recommendations(db_session, session_id=session_row.id, recs=recs)

    result = await db_session.execute(
        select(ModernizeRecommendation)
        .where(ModernizeRecommendation.session_id == session_row.id)
        .order_by(ModernizeRecommendation.idx.asc())
    )
    rows = list(result.scalars().all())
    assert len(rows) == 2
    assert rows[0].assigned_agent == "api"
    assert rows[1].depends_on == [0]
    assert rows[1].wave > rows[0].wave


@pytest.mark.asyncio
async def test_upsert_recommendations_preserves_user_edits_and_linear_mapping(
    db_session: AsyncSession,
) -> None:
    session_row = await _make_session(db_session)
    recs = [_rec_dict("upgrade", "pkg a"), _rec_dict("upgrade", "pkg b")]
    await _upsert_recommendations(db_session, session_id=session_row.id, recs=recs)

    result = await db_session.execute(
        select(ModernizeRecommendation)
        .where(ModernizeRecommendation.session_id == session_row.id)
        .order_by(ModernizeRecommendation.idx.asc())
    )
    rows = list(result.scalars().all())
    rows[0].selected = False
    rows[0].priority = 5
    rows[1].linear_issue_id = "issue-1"
    rows[1].linear_identifier = "CE-999"
    await db_session.commit()

    # 재분석: idx=0 은 갱신, idx=1 은 결과에서 사라짐(짧아짐) — Linear 매핑 보존되어야 함
    new_recs = [_rec_dict("upgrade", "pkg a (재분석 갱신됨)")]
    await _upsert_recommendations(db_session, session_id=session_row.id, recs=new_recs)

    result = await db_session.execute(
        select(ModernizeRecommendation)
        .where(ModernizeRecommendation.session_id == session_row.id)
        .order_by(ModernizeRecommendation.idx.asc())
    )
    rows = list(result.scalars().all())
    assert len(rows) == 2  # idx=1 은 linear_issue_id 존재 → 삭제되지 않음

    row0 = next(r for r in rows if r.idx == 0)
    assert row0.title == "pkg a (재분석 갱신됨)"  # AI 콘텐츠는 갱신
    assert row0.selected is False  # 사용자 편집 보존
    assert row0.priority == 5  # 사용자 편집 보존

    row1 = next(r for r in rows if r.idx == 1)
    assert row1.linear_issue_id == "issue-1"  # Linear 매핑 보존
    assert row1.linear_identifier == "CE-999"


@pytest.mark.asyncio
async def test_generate_plan_artifacts_requires_tobe_approval(db_session: AsyncSession) -> None:
    session_row = await _make_session(db_session)
    await _upsert_recommendations(
        db_session, session_id=session_row.id, recs=[_rec_dict("upgrade", "pkg a")]
    )

    with pytest.raises(plan_generation.TobeNotApprovedError):
        await plan_generation.generate_plan_artifacts(db_session, session_row)


@pytest.mark.asyncio
async def test_generate_plan_artifacts_requires_recommendations(db_session: AsyncSession) -> None:
    session_row = await _make_session(db_session)
    db_session.add(
        ModernizePhaseArtifact(
            session_id=session_row.id,
            phase="tobe",
            artifact_type="tobe_stack",
            approved_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    with pytest.raises(plan_generation.NoRecommendationsError):
        await plan_generation.generate_plan_artifacts(db_session, session_row)


@pytest.mark.asyncio
async def test_generate_plan_artifacts_creates_plan_json_and_md(db_session: AsyncSession) -> None:
    session_row = await _make_session(db_session)
    await _upsert_recommendations(
        db_session,
        session_id=session_row.id,
        recs=[
            _rec_dict("migrate", "schema", target_path="clickeye-api/schema.sql"),
            _rec_dict("refactor", "app code", target_path="clickeye-api/app/main.py"),
        ],
    )
    db_session.add(
        ModernizePhaseArtifact(
            session_id=session_row.id,
            phase="tobe",
            artifact_type="tobe_stack",
            approved_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    json_artifact, summary_artifact = await plan_generation.generate_plan_artifacts(
        db_session, session_row
    )

    assert json_artifact.artifact_type == "plan_json"
    assert json_artifact.content_json["session_id"] == str(session_row.id)
    assert len(json_artifact.content_json["waves"]) >= 1
    assert summary_artifact.artifact_type == "plan_summary"
    assert "Wave" in (summary_artifact.content_md or "")
    assert json_artifact.approved_at is None  # 새로 생성된 산출물은 미승인 상태

    await db_session.refresh(session_row)
    assert session_row.current_phase == "plan"


@pytest.mark.asyncio
async def test_generate_plan_artifacts_resets_approval_on_regeneration(
    db_session: AsyncSession,
) -> None:
    session_row = await _make_session(db_session)
    await _upsert_recommendations(
        db_session, session_id=session_row.id, recs=[_rec_dict("upgrade", "pkg a")]
    )
    db_session.add(
        ModernizePhaseArtifact(
            session_id=session_row.id,
            phase="tobe",
            artifact_type="tobe_stack",
            approved_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    json_artifact, _ = await plan_generation.generate_plan_artifacts(db_session, session_row)
    json_artifact.approved_at = datetime.now(UTC)
    await db_session.commit()

    # 재생성 — 동일 artifact_type 행을 upsert 하며 approved_at 초기화
    json_artifact_2, _ = await plan_generation.generate_plan_artifacts(db_session, session_row)
    assert json_artifact_2.id == json_artifact.id
    assert json_artifact_2.approved_at is None
