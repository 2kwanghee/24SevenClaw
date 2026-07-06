"""Modernize 6단계 Phase 모델(current_phase 컬럼 + modernize_phase_artifacts) 단위 테스트.

기존 status 파이프라인과 병행 도입되는 축이므로, 기존 필드가 그대로 동작하는지와
신규 필드/테이블의 기본값·CRUD를 검증한다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.modernize_phase_artifact import ModernizePhaseArtifact
from app.models.modernize_session import ModernizeSession
from app.models.user import User
from app.schemas.modernize import (
    ModernizePhaseArtifactResponse,
    ModernizeSessionResponse,
    RequirementsArtifactContent,
    StackDescriptor,
)


async def _make_user(db: AsyncSession) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", display_name="Tester")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_modernize_session_current_phase_defaults_to_asis(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    session_row = ModernizeSession(
        user_id=user.id,
        repo_full_name="acme/widgets",
        scenario="versionup",
        status="pending",
    )
    db_session.add(session_row)
    await db_session.commit()
    await db_session.refresh(session_row)

    assert session_row.current_phase == "asis"
    assert session_row.status == "pending"  # 기존 status 축 무영향 확인

    resp = ModernizeSessionResponse.model_validate(session_row)
    assert resp.current_phase == "asis"


@pytest.mark.asyncio
async def test_modernize_phase_artifact_crud(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    session_row = ModernizeSession(
        user_id=user.id,
        repo_full_name="acme/widgets",
        scenario="versionup",
        status="pending",
    )
    db_session.add(session_row)
    await db_session.commit()
    await db_session.refresh(session_row)

    content = RequirementsArtifactContent(
        as_is_stack=StackDescriptor(
            db_type="postgresql", db_version="12", runtime="python", runtime_version="3.8"
        ),
        to_be_stack=StackDescriptor(
            db_type="postgresql", db_version="16", runtime="python", runtime_version="3.12"
        ),
        notes_md="레거시 psycopg2 → asyncpg 전환 필요",
    )

    artifact = ModernizePhaseArtifact(
        session_id=session_row.id,
        phase="requirements",
        artifact_type="requirements_stack",
        content_json=content.model_dump(),
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    assert artifact.approved_at is None

    resp = ModernizePhaseArtifactResponse.model_validate(artifact)
    assert resp.phase == "requirements"
    parsed = RequirementsArtifactContent.model_validate(resp.content_json)
    assert parsed.as_is_stack.db_version == "12"
    assert parsed.to_be_stack.db_version == "16"
    assert parsed.requirement_tags == []  # 기본값 — 하위 호환


@pytest.mark.asyncio
async def test_pipeline_advances_phase_to_requirements_after_asis(db_session: AsyncSession) -> None:
    """analyzing 완료(status=ready) 후 current_phase 가 asis→requirements 로 전이되는지 확인."""
    from app.services.modernize import pipeline

    user = await _make_user(db_session)
    session_row = ModernizeSession(
        user_id=user.id,
        repo_full_name="acme/widgets",
        scenario="versionup",
        status="ready",
    )
    db_session.add(session_row)
    await db_session.commit()
    await db_session.refresh(session_row)

    assert session_row.current_phase == "asis"

    await pipeline._advance_phase(db_session, session_row.id, phase="requirements")  # noqa: SLF001
    await db_session.refresh(session_row)

    assert session_row.current_phase == "requirements"
