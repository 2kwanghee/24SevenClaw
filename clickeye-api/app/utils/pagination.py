"""페이지네이션 유틸리티 — PageParams, Page, paginate."""

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PageParams:
    """page/page_size 기반 페이지네이션 파라미터."""

    page: int = field(default=1)
    page_size: int = field(default=20)

    @property
    def limit(self) -> int:
        return self.page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Page[T](BaseModel):
    """페이지네이션 응답 래퍼."""

    items: list[T]
    total: int
    page: int
    page_size: int

    model_config = {"from_attributes": True}


async def paginate(
    db: AsyncSession,
    stmt: Select[Any],
    params: PageParams,
) -> tuple[list[Any], int]:
    """SELECT 쿼리에 페이지네이션을 적용하여 (items, total) 튜플로 반환.

    반환된 items 리스트와 total 수를 사용해 Page 객체를 구성할 수 있다.
    """
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total: int = total_result.scalar_one()

    paginated = stmt.limit(params.limit).offset(params.offset)
    rows_result = await db.execute(paginated)
    items = list(rows_result.scalars().all())
    return items, total
