"""DB 유틸리티 — get_or_404 헬퍼."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.core.exceptions import AppError
from app.database import Base


async def get_or_404[T: Base](
    db: AsyncSession,
    model: type[T],
    *conditions: ColumnElement[Any],
    code: str,
    message: str,
) -> T:
    """조건에 맞는 단일 ORM 객체를 반환하고, 없으면 AppError(404)를 발생시킨다."""
    result = await db.execute(select(model).where(*conditions))
    obj = result.scalar_one_or_none()
    if obj is None:
        raise AppError(code, message, 404)
    return obj
