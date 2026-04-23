"""paginate 유틸리티 단위 테스트."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.utils.pagination import PageParams, paginate


async def _create_orgs(db: AsyncSession, count: int) -> None:
    for i in range(count):
        db.add(Organization(company_name=f"회사 {i + 1}"))
    await db.commit()


@pytest.mark.asyncio
async def test_paginate_empty(db_session: AsyncSession) -> None:
    """레코드가 없을 때 빈 리스트와 total=0을 반환한다."""
    stmt = select(Organization)
    items, total = await paginate(db_session, stmt, PageParams(page=1, page_size=10))
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_paginate_first_page(db_session: AsyncSession) -> None:
    """첫 페이지에서 page_size 개수만큼 반환하고 total은 전체 수다."""
    await _create_orgs(db_session, 5)

    stmt = select(Organization)
    items, total = await paginate(db_session, stmt, PageParams(page=1, page_size=3))
    assert len(items) == 3
    assert total == 5


@pytest.mark.asyncio
async def test_paginate_second_page(db_session: AsyncSession) -> None:
    """두 번째 페이지에서 나머지 레코드를 반환한다."""
    await _create_orgs(db_session, 5)

    stmt = select(Organization)
    items, total = await paginate(db_session, stmt, PageParams(page=2, page_size=3))
    assert len(items) == 2
    assert total == 5


@pytest.mark.asyncio
async def test_paginate_out_of_range(db_session: AsyncSession) -> None:
    """범위를 벗어난 페이지는 빈 리스트를 반환하고 total은 전체 수다."""
    await _create_orgs(db_session, 3)

    stmt = select(Organization)
    items, total = await paginate(db_session, stmt, PageParams(page=10, page_size=10))
    assert items == []
    assert total == 3
