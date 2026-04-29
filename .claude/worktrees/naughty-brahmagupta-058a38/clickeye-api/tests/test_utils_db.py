"""get_or_404 유틸리티 단위 테스트."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.organization import Organization
from app.utils.db import get_or_404


@pytest.mark.asyncio
async def test_get_or_404_returns_existing_object(db_session: AsyncSession) -> None:
    """존재하는 레코드를 조건에 맞게 조회하면 해당 객체를 반환한다."""
    org = Organization(company_name="테스트 회사")
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    found = await get_or_404(
        db_session,
        Organization,
        Organization.id == org.id,
        code="ORG_NOT_FOUND",
        message="조직을 찾을 수 없습니다",
    )
    assert found.id == org.id
    assert found.company_name == "테스트 회사"


@pytest.mark.asyncio
async def test_get_or_404_raises_app_error_for_missing(db_session: AsyncSession) -> None:
    """존재하지 않는 ID로 조회하면 AppError(404)를 발생시킨다."""
    nonexistent_id = uuid.uuid4()

    with pytest.raises(AppError) as exc_info:
        await get_or_404(
            db_session,
            Organization,
            Organization.id == nonexistent_id,
            code="ORG_NOT_FOUND",
            message="조직을 찾을 수 없습니다",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.code == "ORG_NOT_FOUND"
