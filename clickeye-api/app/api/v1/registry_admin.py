"""Registry Admin API — Agent/Skill/MCPServer CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.registry import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
    HookCreate,
    HookListResponse,
    HookResponse,
    HookUpdate,
    MCPServerCreate,
    MCPServerResponse,
    MCPServerUpdate,
    RegistryItemListResponse,
    SkillCreate,
    SkillListResponse,
    SkillResponse,
    SkillUpdate,
)
from app.services.registry_service import RegistryService

router = APIRouter(prefix="/admin/registry", tags=["admin-registry"])


# ─── Agents ───

@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    category: str | None = Query(None),
    is_public: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> AgentListResponse:
    svc = RegistryService(db)
    items, total = await svc.list_agents(
        category=category, is_public=is_public, offset=offset, limit=limit
    )
    return AgentListResponse(
        items=[AgentResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    svc = RegistryService(db)
    item = await svc.create_agent(data)
    return AgentResponse.model_validate(item)


@router.get("/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    svc = RegistryService(db)
    item = await svc.get_agent(agent_id)
    return AgentResponse.model_validate(item)


@router.put("/agents/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    data: AgentUpdate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> AgentResponse:
    svc = RegistryService(db)
    item = await svc.update_agent(agent_id, data)
    return AgentResponse.model_validate(item)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = RegistryService(db)
    await svc.delete_agent(agent_id)


# ─── Skills ───

@router.get("/skills", response_model=SkillListResponse)
async def list_skills(
    category: str | None = Query(None),
    is_public: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> SkillListResponse:
    svc = RegistryService(db)
    items, total = await svc.list_skills(
        category=category, is_public=is_public, offset=offset, limit=limit
    )
    return SkillListResponse(
        items=[SkillResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    data: SkillCreate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    svc = RegistryService(db)
    item = await svc.create_skill(data)
    return SkillResponse.model_validate(item)


@router.get("/skills/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    svc = RegistryService(db)
    item = await svc.get_skill(skill_id)
    return SkillResponse.model_validate(item)


@router.put("/skills/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: UUID,
    data: SkillUpdate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> SkillResponse:
    svc = RegistryService(db)
    item = await svc.update_skill(skill_id, data)
    return SkillResponse.model_validate(item)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = RegistryService(db)
    await svc.delete_skill(skill_id)


# ─── Hooks ───

@router.get("/hooks", response_model=HookListResponse)
async def list_hooks(
    category: str | None = Query(None),
    is_public: bool | None = Query(None),
    event: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> HookListResponse:
    svc = RegistryService(db)
    items, total = await svc.list_hooks(
        category=category, is_public=is_public, event=event, offset=offset, limit=limit
    )
    return HookListResponse(
        items=[HookResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post("/hooks", response_model=HookResponse, status_code=status.HTTP_201_CREATED)
async def create_hook(
    data: HookCreate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> HookResponse:
    svc = RegistryService(db)
    item = await svc.create_hook(data)
    return HookResponse.model_validate(item)


@router.get("/hooks/{hook_id}", response_model=HookResponse)
async def get_hook(
    hook_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> HookResponse:
    svc = RegistryService(db)
    item = await svc.get_hook(hook_id)
    return HookResponse.model_validate(item)


@router.put("/hooks/{hook_id}", response_model=HookResponse)
async def update_hook(
    hook_id: UUID,
    data: HookUpdate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> HookResponse:
    svc = RegistryService(db)
    item = await svc.update_hook(hook_id, data)
    return HookResponse.model_validate(item)


@router.delete("/hooks/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hook(
    hook_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = RegistryService(db)
    await svc.delete_hook(hook_id)


# ─── MCP Servers ───

@router.get("/mcp-servers", response_model=RegistryItemListResponse)
async def list_mcp_servers(
    category: str | None = Query(None),
    is_public: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> RegistryItemListResponse:
    svc = RegistryService(db)
    items, total = await svc.list_mcp_servers(
        category=category, is_public=is_public, offset=offset, limit=limit
    )
    return RegistryItemListResponse(
        items=[MCPServerResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post("/mcp-servers", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    data: MCPServerCreate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> MCPServerResponse:
    svc = RegistryService(db)
    item = await svc.create_mcp_server(data)
    return MCPServerResponse.model_validate(item)


@router.get("/mcp-servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> MCPServerResponse:
    svc = RegistryService(db)
    item = await svc.get_mcp_server(server_id)
    return MCPServerResponse.model_validate(item)


@router.put("/mcp-servers/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: UUID,
    data: MCPServerUpdate,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> MCPServerResponse:
    svc = RegistryService(db)
    item = await svc.update_mcp_server(server_id, data)
    return MCPServerResponse.model_validate(item)


@router.delete("/mcp-servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: UUID,
    user: User = Depends(require_permission("registry:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = RegistryService(db)
    await svc.delete_mcp_server(server_id)
