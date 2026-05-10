from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting
from app.models.user import User


class AppSettingService:
    DEFAULT_VARIANT_COUNT = 3
    DEFAULT_RAG_TOP_K = 8

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_variant_count(self) -> int:
        row = await self.db.get(AppSetting, "prototype_variant_count")
        if row is None:
            return self.DEFAULT_VARIANT_COUNT
        val = row.value
        if isinstance(val, dict):
            return int(val.get("value", self.DEFAULT_VARIANT_COUNT))
        return int(val)

    async def get_rag_top_k(self) -> int:
        row = await self.db.get(AppSetting, "prototype_rag_top_k")
        if row is None:
            return self.DEFAULT_RAG_TOP_K
        val = row.value
        if isinstance(val, dict):
            return int(val.get("value", self.DEFAULT_RAG_TOP_K))
        return int(val)

    async def set_variant_count(self, value: int, actor: User) -> AppSetting:
        value = max(2, min(5, value))
        row = await self.db.get(AppSetting, "prototype_variant_count")
        if row is None:
            row = AppSetting(
                key="prototype_variant_count",
                value={"value": value, "min": 2, "max": 5},
                description="프로토타입 제안 개수 (2-5, 기본 3)",
                updated_by=actor.id,
            )
            self.db.add(row)
        else:
            row.value = {"value": value, "min": 2, "max": 5}
            row.updated_by = actor.id  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def set_rag_top_k(self, value: int, actor: User) -> AppSetting:
        value = max(1, min(20, value))
        row = await self.db.get(AppSetting, "prototype_rag_top_k")
        if row is None:
            row = AppSetting(
                key="prototype_rag_top_k",
                value={"value": value, "min": 1, "max": 20},
                description="Claude 참조용 카탈로그 top-k (1-20, 기본 8)",
                updated_by=actor.id,
            )
            self.db.add(row)
        else:
            row.value = {"value": value, "min": 1, "max": 20}
            row.updated_by = actor.id  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def get_all(self) -> list[AppSetting]:
        result = await self.db.execute(select(AppSetting).order_by(AppSetting.key))
        return list(result.scalars().all())
