"""생성 엔진용 카탈로그 어댑터.

공개 함수:
- prefetch_for_generator(db, agent_ids, skill_ids, hook_ids, mcp_ids) → CatalogPrefetch
- get_selected_agents/skills/hooks/mcps(prefetch)
- get_env_var_definitions(prefetch) / find_stack(stack_id)

기존 하드코딩 AGENTS/SKILLS 상수는 DB로 대체됐으므로 제거됨.
STACKS 는 로컬 JSON 이나 config 로 이동 예정이며 이번엔 그대로 유지.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.catalog_service import get_catalog_service

# 기술 스택 카탈로그 (DB 이관 대상 아님 — 위저드 step 3)
STACKS: list[dict[str, Any]] = [
    {
        "id": "fastapi-nextjs",
        "name": "FastAPI + Next.js",
        "backend": "FastAPI + SQLAlchemy",
        "frontend": "Next.js 15 + Tailwind",
        "test": {"backend": "uv run pytest --tb=short -q", "frontend": "npm run test"},
        "lint": {"backend": "uv run ruff check .", "frontend": "npm run lint"},
        "typecheck": {"backend": "uv run mypy app/", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "django-react",
        "name": "Django + React",
        "backend": "Django + DRF",
        "frontend": "React + Vite",
        "test": {"backend": "uv run pytest --tb=short -q", "frontend": "npm run test"},
        "lint": {"backend": "uv run ruff check .", "frontend": "npm run lint"},
        "typecheck": {"backend": "uv run mypy .", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "express-vue",
        "name": "Express + Vue",
        "backend": "Express + Prisma",
        "frontend": "Vue 3 + Vite",
        "test": {"backend": "npm run test:backend", "frontend": "npm run test"},
        "lint": {"backend": "npx eslint src/", "frontend": "npm run lint"},
        "typecheck": {"backend": "npx tsc --noEmit", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "nestjs-nextjs",
        "name": "NestJS + Next.js",
        "backend": "NestJS + TypeORM",
        "frontend": "Next.js 15",
        "test": {"backend": "npm run test:backend", "frontend": "npm run test"},
        "lint": {"backend": "npx eslint src/", "frontend": "npm run lint"},
        "typecheck": {"backend": "npx tsc --noEmit", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "flask-react",
        "name": "Flask + React",
        "backend": "Flask + SQLAlchemy",
        "frontend": "React + Vite",
        "test": {"backend": "uv run pytest --tb=short -q", "frontend": "npm run test"},
        "lint": {"backend": "uv run ruff check .", "frontend": "npm run lint"},
        "typecheck": {"backend": "uv run mypy .", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "custom",
        "name": "커스텀 (직접 입력)",
        "backend": "",
        "frontend": "",
        "test": {"backend": "", "frontend": ""},
        "lint": {"backend": "", "frontend": ""},
        "typecheck": {"backend": "", "frontend": ""},
    },
]


@dataclass
class CatalogPrefetch:
    """generate_all() 에 전달하는 사전 로드된 카탈로그 데이터."""

    agents: list[dict[str, Any]] = field(default_factory=list)
    skills: list[dict[str, Any]] = field(default_factory=list)
    hooks: list[dict[str, Any]] = field(default_factory=list)
    mcps: list[dict[str, Any]] = field(default_factory=list)


async def prefetch_for_generator(
    db: AsyncSession,
    agent_ids: list[str],
    skill_ids: list[str],
    hook_ids: list[str] | None = None,
    mcp_ids: list[str] | None = None,
) -> CatalogPrefetch:
    """DB에서 카탈로그를 미리 로드하여 sync generate_all 에 주입할 수 있게 반환."""
    svc = get_catalog_service()
    agents = await svc.get_agents_by_slugs(db, agent_ids)
    skills = await svc.get_skills_by_slugs(db, skill_ids)
    hooks = await svc.get_hooks_by_slugs(db, hook_ids or [])
    mcps = await svc.get_mcps_by_slugs(db, mcp_ids or [])
    return CatalogPrefetch(agents=agents, skills=skills, hooks=hooks, mcps=mcps)


def get_selected_agents(
    agent_ids: list[str], prefetch: CatalogPrefetch | None = None
) -> list[dict[str, Any]]:
    """선택된 에이전트 + required 에이전트 반환.

    prefetch 가 있으면 사전 로드 데이터를 사용하고 (slug 필터 이미 적용됨),
    없으면 빈 리스트를 반환한다 (caller 가 prefetch 없이 호출하는 경우 방지).
    """
    if prefetch is not None:
        return prefetch.agents
    return []


def get_selected_skills(
    workflow_ids: list[str], prefetch: CatalogPrefetch | None = None
) -> list[dict[str, Any]]:
    """선택된 워크플로우에 해당하는 스킬 반환."""
    if prefetch is not None:
        return prefetch.skills
    return []


def get_selected_hooks(
    hook_ids: list[str], prefetch: CatalogPrefetch | None = None
) -> list[dict[str, Any]]:
    """선택된 훅 반환."""
    if prefetch is not None:
        return prefetch.hooks
    return []


def get_selected_mcps(
    mcp_ids: list[str], prefetch: CatalogPrefetch | None = None
) -> list[dict[str, Any]]:
    """선택된 MCP 서버 반환."""
    if prefetch is not None:
        return prefetch.mcps
    return []


def get_env_var_definitions(
    workflow_ids: list[str], prefetch: CatalogPrefetch | None = None
) -> list[dict[str, Any]]:
    """선택된 워크플로우(스킬+훅)에서 필요한 환경 변수 정의를 수집."""
    env_vars: list[dict[str, Any]] = []
    seen: set[str] = set()

    skills = get_selected_skills(workflow_ids, prefetch)
    for skill in skills:
        for var in skill.get("env_vars", []):
            var_name = var.get("name", "")
            if var_name and var_name not in seen:
                env_vars.append(
                    {
                        **var,
                        "skill_id": skill["id"],
                        "skill_name": skill.get("label", skill["id"]),
                    }
                )
                seen.add(var_name)

    hooks = get_selected_hooks([], prefetch)
    for hook in hooks:
        for var in hook.get("env_vars", []):
            var_name = var.get("name", "")
            if var_name and var_name not in seen:
                env_vars.append(
                    {
                        **var,
                        "skill_id": hook["id"],
                        "skill_name": hook.get("label", hook["id"]),
                    }
                )
                seen.add(var_name)

    return env_vars


def find_stack(stack_id: str) -> dict[str, Any] | None:
    """스택 ID로 카탈로그 항목 검색."""
    return next((s for s in STACKS if s["id"] == stack_id), None)
