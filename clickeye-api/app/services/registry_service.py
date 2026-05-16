"""Registry Admin 서비스 — Agent/Skill/MCPServer CRUD."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.registry import Agent, Hook, MCPServer, Skill
from app.schemas.registry import (
    AgentCreate,
    AgentUpdate,
    HookCreate,
    HookUpdate,
    MCPServerCreate,
    MCPServerUpdate,
    SkillCreate,
    SkillUpdate,
)

_MODEL_MAP: dict[str, type[Agent | Skill | Hook | MCPServer]] = {
    "agent": Agent,
    "skill": Skill,
    "hook": Hook,
    "mcp_server": MCPServer,
}


class RegistryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Generic helpers ───

    async def _list(
        self,
        model: type[Any],
        *,
        category: str | None = None,
        is_public: bool | None = None,
        domain: str | None = None,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Any], int]:
        conditions: list[Any] = []
        if category:
            conditions.append(model.category == category)
        if is_public is not None:
            conditions.append(model.is_public == is_public)
        if domain:
            # JSON 배열에 domain 문자열 포함 여부 (PostgreSQL JSON contains)
            conditions.append(sa.cast(model.domains, sa.Text).contains(f'"{domain}"'))
        if tag:
            conditions.append(sa.cast(model.tags, sa.Text).contains(f'"{tag}"'))

        count_stmt = select(func.count()).select_from(model).where(*conditions)
        total = int((await self.db.execute(count_stmt)).scalar_one())

        stmt = (
            select(model).where(*conditions).order_by(model.name.asc()).offset(offset).limit(limit)
        )
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def _get(self, model: type[Any], item_id: UUID) -> Any:
        item = await self.db.get(model, item_id)
        if item is None:
            raise AppError("REGISTRY_NOT_FOUND", "레지스트리 항목을 찾을 수 없습니다", 404)
        return item

    async def _get_by_slug(self, model: type[Any], slug: str) -> Any:
        stmt = select(model).where(model.slug == slug)
        result = await self.db.execute(stmt)
        item = result.scalar_one_or_none()
        if item is None:
            raise AppError("REGISTRY_NOT_FOUND", "레지스트리 항목을 찾을 수 없습니다", 404)
        return item

    async def _create(self, model: type[Any], data: Any) -> Any:
        stmt = select(model).where(model.slug == data.slug)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise AppError("SLUG_CONFLICT", "이미 사용 중인 slug입니다", 409)

        item = model(**data.model_dump())
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def _update(self, model: type[Any], item_id: UUID, data: Any) -> Any:
        item = await self._get(model, item_id)
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        item.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def _delete(self, model: type[Any], item_id: UUID) -> None:
        item = await self._get(model, item_id)
        await self.db.delete(item)
        await self.db.commit()

    # ─── Agent ───

    async def list_agents(
        self,
        *,
        category: str | None = None,
        is_public: bool | None = None,
        domain: str | None = None,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Agent], int]:
        return await self._list(
            Agent,
            category=category,
            is_public=is_public,
            domain=domain,
            tag=tag,
            offset=offset,
            limit=limit,
        )

    async def get_agent(self, agent_id: UUID) -> Agent:
        return await self._get(Agent, agent_id)  # type: ignore[no-any-return]

    async def create_agent(self, data: AgentCreate) -> Agent:
        return await self._create(Agent, data)  # type: ignore[no-any-return]

    async def update_agent(self, agent_id: UUID, data: AgentUpdate) -> Agent:
        return await self._update(Agent, agent_id, data)  # type: ignore[no-any-return]

    async def delete_agent(self, agent_id: UUID) -> None:
        await self._delete(Agent, agent_id)

    # ─── Skill ───

    async def list_skills(
        self,
        *,
        category: str | None = None,
        is_public: bool | None = None,
        domain: str | None = None,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Skill], int]:
        return await self._list(
            Skill,
            category=category,
            is_public=is_public,
            domain=domain,
            tag=tag,
            offset=offset,
            limit=limit,
        )

    async def get_skill(self, skill_id: UUID) -> Skill:
        return await self._get(Skill, skill_id)  # type: ignore[no-any-return]

    async def create_skill(self, data: SkillCreate) -> Skill:
        return await self._create(Skill, data)  # type: ignore[no-any-return]

    async def update_skill(self, skill_id: UUID, data: SkillUpdate) -> Skill:
        return await self._update(Skill, skill_id, data)  # type: ignore[no-any-return]

    async def delete_skill(self, skill_id: UUID) -> None:
        await self._delete(Skill, skill_id)

    # ─── Hook ───

    async def list_hooks(
        self,
        *,
        category: str | None = None,
        is_public: bool | None = None,
        event: str | None = None,
        domain: str | None = None,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Hook], int]:
        conditions: list[Any] = []
        if category:
            conditions.append(Hook.category == category)
        if is_public is not None:
            conditions.append(Hook.is_public == is_public)
        if event:
            conditions.append(Hook.event == event)
        if domain:
            conditions.append(sa.cast(Hook.domains, sa.Text).contains(f'"{domain}"'))
        if tag:
            conditions.append(sa.cast(Hook.tags, sa.Text).contains(f'"{tag}"'))

        count_stmt = select(func.count()).select_from(Hook).where(*conditions)
        total = int((await self.db.execute(count_stmt)).scalar_one())

        stmt = select(Hook).where(*conditions).order_by(Hook.name.asc()).offset(offset).limit(limit)
        items = list((await self.db.execute(stmt)).scalars().all())
        return items, total

    async def get_hook(self, hook_id: UUID) -> Hook:
        return await self._get(Hook, hook_id)  # type: ignore[no-any-return]

    async def create_hook(self, data: HookCreate) -> Hook:
        return await self._create(Hook, data)  # type: ignore[no-any-return]

    async def update_hook(self, hook_id: UUID, data: HookUpdate) -> Hook:
        return await self._update(Hook, hook_id, data)  # type: ignore[no-any-return]

    async def delete_hook(self, hook_id: UUID) -> None:
        await self._delete(Hook, hook_id)

    # ─── MCPServer ───

    async def list_mcp_servers(
        self,
        *,
        category: str | None = None,
        is_public: bool | None = None,
        domain: str | None = None,
        tag: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[MCPServer], int]:
        return await self._list(
            MCPServer,
            category=category,
            is_public=is_public,
            domain=domain,
            tag=tag,
            offset=offset,
            limit=limit,
        )

    async def get_mcp_server(self, server_id: UUID) -> MCPServer:
        return await self._get(MCPServer, server_id)  # type: ignore[no-any-return]

    async def create_mcp_server(self, data: MCPServerCreate) -> MCPServer:
        return await self._create(MCPServer, data)  # type: ignore[no-any-return]

    async def update_mcp_server(self, server_id: UUID, data: MCPServerUpdate) -> MCPServer:
        return await self._update(MCPServer, server_id, data)  # type: ignore[no-any-return]

    async def delete_mcp_server(self, server_id: UUID) -> None:
        await self._delete(MCPServer, server_id)
