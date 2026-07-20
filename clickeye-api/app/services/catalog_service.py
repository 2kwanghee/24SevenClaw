"""카탈로그 조회 서비스 — DB SSOT (agents / skills / hooks).

platforms / pipelines 는 기존 JSON 파일에서 계속 읽는다.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.registry import Agent, Hook, MCPServer, Skill

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "catalog"
_JSON_TYPES = ("platforms", "pipelines")


@lru_cache(maxsize=4)
def _load_json(catalog_type: str) -> list[dict[str, Any]]:
    """JSON 파일을 읽고 캐싱한다 (platforms / pipelines 전용)."""
    file_path = _DATA_DIR / f"{catalog_type}.json"
    with file_path.open(encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)
    return data


def _agent_to_dict(a: Agent) -> dict[str, Any]:
    return {
        "id": a.slug,
        "label": a.name,
        "label_en": a.name_en,
        "description": a.description,
        "description_en": a.description_en,
        "category": a.category,
        "required": a.required,
        "output_file": a.output_file,
        "dependencies": a.dependencies or [],
    }


def _skill_to_dict(s: Skill) -> dict[str, Any]:
    return {
        "id": s.slug,
        "label": s.name,
        "label_en": s.name_en,
        "description": s.description,
        "description_en": s.description_en,
        "category": s.category,
        "required": s.required,
        "output_file": s.output_file,
        "dependencies": s.dependencies or [],
        "hook_events": s.hook_events or [],
        "env_vars": s.env_vars or [],
    }


def _hook_to_dict(h: Hook) -> dict[str, Any]:
    return {
        "id": h.slug,
        "label": h.name,
        "label_en": h.name_en,
        "description": h.description,
        "description_en": h.description_en,
        "category": h.category,
        "required": h.required,
        "event": h.event,
        "output_file": h.output_file,
    }


def _mcp_to_dict(m: MCPServer) -> dict[str, Any]:
    return {
        "id": m.slug,
        "label": m.name,
        "label_en": m.name_en,
        "description": m.description,
        "description_en": m.description_en,
        "category": m.category,
        "body_md": m.body_md,
        "body_md_en": m.body_md_en,
    }


class CatalogService:
    """카탈로그 데이터 조회 서비스 (DB SSOT)."""

    # platforms / pipelines 는 기존 JSON 방식 유지
    def get_json(self, catalog_type: str) -> list[dict[str, Any]]:
        if catalog_type not in _JSON_TYPES:
            msg = f"JSON 카탈로그 타입이 아닙니다: {catalog_type}"
            raise ValueError(msg)
        return _load_json(catalog_type)

    async def list_agents(self, db: AsyncSession) -> list[dict[str, Any]]:
        stmt = select(Agent).where(Agent.is_public == True).order_by(Agent.name.asc())  # noqa: E712
        result = await db.execute(stmt)
        return [_agent_to_dict(a) for a in result.scalars().all()]

    async def list_skills(self, db: AsyncSession) -> list[dict[str, Any]]:
        stmt = select(Skill).where(Skill.is_public == True).order_by(Skill.name.asc())  # noqa: E712
        result = await db.execute(stmt)
        return [_skill_to_dict(s) for s in result.scalars().all()]

    async def list_hooks(self, db: AsyncSession) -> list[dict[str, Any]]:
        stmt = select(Hook).where(Hook.is_public == True).order_by(Hook.name.asc())  # noqa: E712
        result = await db.execute(stmt)
        return [_hook_to_dict(h) for h in result.scalars().all()]

    async def get_agents_by_slugs(self, db: AsyncSession, slugs: list[str]) -> list[dict[str, Any]]:
        """ZIP 생성 엔진용 — slug 목록 + required 에이전트를 반환."""
        stmt = (
            select(Agent)
            .where(
                (Agent.slug.in_(slugs)) | (Agent.required == True)  # noqa: E712
            )
            .order_by(Agent.name.asc())
        )
        result = await db.execute(stmt)
        agents = result.scalars().all()
        # body_md 포함 반환
        return [
            {
                **_agent_to_dict(a),
                "body_md": a.body_md,
                "body_md_en": a.body_md_en,
                "template": f"agents/{a.output_file}.j2" if a.output_file else None,
            }
            for a in agents
        ]

    async def get_skills_by_slugs(self, db: AsyncSession, slugs: list[str]) -> list[dict[str, Any]]:
        """ZIP 생성 엔진용 — slug 목록에 해당하는 스킬을 반환."""
        stmt = select(Skill).where(Skill.slug.in_(slugs)).order_by(Skill.name.asc())
        result = await db.execute(stmt)
        skills = result.scalars().all()
        return [
            {
                **_skill_to_dict(s),
                "body_md": s.body_md,
                "body_md_en": s.body_md_en,
                "template": f"skills/{s.output_file}.j2" if s.output_file else None,
            }
            for s in skills
        ]

    async def get_hooks_by_slugs(self, db: AsyncSession, slugs: list[str]) -> list[dict[str, Any]]:
        """ZIP 생성 엔진용 — slug 목록에 해당하는 훅을 반환."""
        stmt = select(Hook).where(Hook.slug.in_(slugs)).order_by(Hook.name.asc())
        result = await db.execute(stmt)
        hooks = result.scalars().all()
        return [
            {
                **_hook_to_dict(h),
                "body_md": h.body_md,
                "body_md_en": h.body_md_en,
                "template": f"hooks/{h.output_file}.j2" if h.output_file else None,
            }
            for h in hooks
        ]

    async def list_mcps(self, db: AsyncSession) -> list[dict[str, Any]]:
        stmt = select(MCPServer).where(MCPServer.is_public == True).order_by(MCPServer.name.asc())  # noqa: E712
        result = await db.execute(stmt)
        return [_mcp_to_dict(m) for m in result.scalars().all()]

    async def get_mcps_by_slugs(self, db: AsyncSession, slugs: list[str]) -> list[dict[str, Any]]:
        """ZIP 생성 엔진용 — slug 목록에 해당하는 MCP 서버를 반환."""
        stmt = select(MCPServer).where(MCPServer.slug.in_(slugs)).order_by(MCPServer.name.asc())
        result = await db.execute(stmt)
        return [_mcp_to_dict(m) for m in result.scalars().all()]


_service = CatalogService()


def get_catalog_service() -> CatalogService:
    return _service
