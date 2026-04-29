"""프로토타입 카탈로그 서비스 — CRUD + 태그 매칭."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.prototype_catalog import PrototypeCatalogEntry, PrototypeTag
from app.schemas.prototype_catalog import (
    PrototypeCatalogEntryCreate,
    PrototypeCatalogEntryUpdate,
    PrototypeTagCreate,
    PrototypeTagUpdate,
)


class PrototypeCatalogService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── CatalogEntry CRUD ─────────────────────────────────────────────────────

    async def list_entries(
        self,
        *,
        tags: list[str] | None = None,
        primary_tag: str | None = None,
        is_active: bool | None = True,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[PrototypeCatalogEntry], int]:
        conditions: list = []
        if is_active is not None:
            conditions.append(PrototypeCatalogEntry.is_active == is_active)
        if primary_tag:
            conditions.append(PrototypeCatalogEntry.primary_tag == primary_tag)

        count_stmt = (
            select(func.count())
            .select_from(PrototypeCatalogEntry)
            .where(*conditions)
        )
        total = int((await self.db.execute(count_stmt)).scalar_one())

        stmt = (
            select(PrototypeCatalogEntry)
            .where(*conditions)
            .order_by(
                PrototypeCatalogEntry.priority.desc(),
                PrototypeCatalogEntry.title.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())

        if tags:
            items = self._filter_by_tags(items, tags)

        return items, total

    async def get_entry(self, entry_id: UUID) -> PrototypeCatalogEntry:
        entry = await self.db.get(PrototypeCatalogEntry, entry_id)
        if entry is None:
            raise AppError("CATALOG_NOT_FOUND", "카탈로그 항목을 찾을 수 없습니다", 404)
        return entry

    async def get_entry_by_slug(self, slug: str) -> PrototypeCatalogEntry:
        stmt = select(PrototypeCatalogEntry).where(PrototypeCatalogEntry.slug == slug)
        entry = (await self.db.execute(stmt)).scalar_one_or_none()
        if entry is None:
            raise AppError("CATALOG_NOT_FOUND", "카탈로그 항목을 찾을 수 없습니다", 404)
        return entry

    async def create_entry(self, data: PrototypeCatalogEntryCreate) -> PrototypeCatalogEntry:
        existing = (
            await self.db.execute(
                select(PrototypeCatalogEntry).where(PrototypeCatalogEntry.slug == data.slug)
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise AppError("SLUG_CONFLICT", "이미 사용 중인 slug입니다", 409)

        entry = PrototypeCatalogEntry(**data.model_dump())
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def update_entry(
        self, entry_id: UUID, data: PrototypeCatalogEntryUpdate
    ) -> PrototypeCatalogEntry:
        entry = await self.get_entry(entry_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(entry, key, value)
        entry.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def delete_entry(self, entry_id: UUID) -> None:
        entry = await self.get_entry(entry_id)
        await self.db.delete(entry)
        await self.db.commit()

    async def match_by_tags(
        self, candidate_tags: list[str], limit: int = 8
    ) -> list[PrototypeCatalogEntry]:
        """태그 overlap이 큰 순으로 활성 카탈로그 엔트리를 반환한다."""
        if not candidate_tags:
            stmt = (
                select(PrototypeCatalogEntry)
                .where(PrototypeCatalogEntry.is_active == True)  # noqa: E712
                .order_by(PrototypeCatalogEntry.priority.desc())
                .limit(limit)
            )
            return list((await self.db.execute(stmt)).scalars().all())

        stmt = (
            select(PrototypeCatalogEntry)
            .where(PrototypeCatalogEntry.is_active == True)  # noqa: E712
        )
        all_entries = list((await self.db.execute(stmt)).scalars().all())

        scored = sorted(
            all_entries,
            key=lambda e: (
                len(set(e.tags or []) & set(candidate_tags)),
                e.priority,
            ),
            reverse=True,
        )
        return scored[:limit]

    # ── PrototypeTag CRUD ─────────────────────────────────────────────────────

    async def list_tags(
        self, *, is_active: bool | None = None
    ) -> tuple[list[PrototypeTag], int]:
        conditions: list = []
        if is_active is not None:
            conditions.append(PrototypeTag.is_active == is_active)

        count_stmt = select(func.count()).select_from(PrototypeTag).where(*conditions)
        total = int((await self.db.execute(count_stmt)).scalar_one())

        stmt = (
            select(PrototypeTag)
            .where(*conditions)
            .order_by(PrototypeTag.sort_order.asc(), PrototypeTag.label.asc())
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def get_tag(self, tag_id: UUID) -> PrototypeTag:
        tag = await self.db.get(PrototypeTag, tag_id)
        if tag is None:
            raise AppError("TAG_NOT_FOUND", "태그를 찾을 수 없습니다", 404)
        return tag

    async def create_tag(self, data: PrototypeTagCreate) -> PrototypeTag:
        existing = (
            await self.db.execute(
                select(PrototypeTag).where(PrototypeTag.slug == data.slug)
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise AppError("SLUG_CONFLICT", "이미 사용 중인 slug입니다", 409)

        tag = PrototypeTag(**data.model_dump())
        self.db.add(tag)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def update_tag(self, tag_id: UUID, data: PrototypeTagUpdate) -> PrototypeTag:
        tag = await self.get_tag(tag_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(tag, key, value)
        await self.db.commit()
        await self.db.refresh(tag)
        return tag

    async def delete_tag(self, tag_id: UUID) -> None:
        tag = await self.get_tag(tag_id)
        await self.db.delete(tag)
        await self.db.commit()

    # ── 내부 유틸 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _filter_by_tags(
        entries: list[PrototypeCatalogEntry], tags: list[str]
    ) -> list[PrototypeCatalogEntry]:
        tag_set = set(tags)
        return [e for e in entries if tag_set & set(e.tags or [])]
