"""BaseService — 공통 서비스 레이어 베이스 클래스."""

from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

_T = TypeVar("_T", bound=Base)


class BaseService:
    """DB 세션을 주입받아 공통 헬퍼를 제공하는 베이스 서비스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def apply_update(self, obj: _T, update: BaseModel, *, commit: bool = True) -> _T:
        """Pydantic partial update 스키마를 ORM 객체 필드에 반영한다.

        exclude_unset=True 로 덤프하므로 요청에 포함된 필드만 변경된다.
        commit=True(기본값)이면 커밋 후 refresh까지 수행한다.
        """
        for key, value in update.model_dump(exclude_unset=True).items():
            setattr(obj, key, value)
        if commit:
            await self.db.commit()
            await self.db.refresh(obj)
        return obj

    async def save(self, obj: Any, *, refresh: bool = True) -> None:
        """ORM 객체를 add → commit하고, refresh=True이면 DB 상태를 다시 로드한다."""
        self.db.add(obj)
        await self.db.commit()
        if refresh:
            await self.db.refresh(obj)
