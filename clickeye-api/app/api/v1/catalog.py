"""카탈로그 조회 엔드포인트 (agents, skills, hooks, platforms, pipelines)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.catalog import CatalogListResponse, CatalogResponse
from app.schemas.registry import localize_registry_item
from app.services.catalog_service import get_catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/agents", response_model=CatalogListResponse)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    locale: str = Query(default="ko", max_length=8),
) -> CatalogListResponse:
    """에이전트 카탈로그 조회 (id, label, description 반환)."""
    svc = get_catalog_service()
    items = await svc.list_agents(db)
    if locale == "en":
        items = [localize_registry_item(i, locale) for i in items]
    return CatalogListResponse(items=items, total=len(items))


@router.get("/skills", response_model=CatalogListResponse)
async def list_skills(
    db: AsyncSession = Depends(get_db),
    locale: str = Query(default="ko", max_length=8),
) -> CatalogListResponse:
    """스킬 카탈로그 조회 (id, label, description 반환)."""
    svc = get_catalog_service()
    items = await svc.list_skills(db)
    if locale == "en":
        items = [localize_registry_item(i, locale) for i in items]
    return CatalogListResponse(items=items, total=len(items))


@router.get("/hooks", response_model=CatalogListResponse)
async def list_hooks(
    db: AsyncSession = Depends(get_db),
    locale: str = Query(default="ko", max_length=8),
) -> CatalogListResponse:
    """훅 카탈로그 조회 (id, label, description 반환)."""
    svc = get_catalog_service()
    items = await svc.list_hooks(db)
    if locale == "en":
        items = [localize_registry_item(i, locale) for i in items]
    return CatalogListResponse(items=items, total=len(items))


@router.get("/mcps", response_model=CatalogListResponse)
async def list_mcps(
    db: AsyncSession = Depends(get_db),
    locale: str = Query(default="ko", max_length=8),
) -> CatalogListResponse:
    """MCP 서버 카탈로그 조회 (id, label, description 반환)."""
    svc = get_catalog_service()
    items = await svc.list_mcps(db)
    if locale == "en":
        items = [localize_registry_item(i, locale) for i in items]
    return CatalogListResponse(items=items, total=len(items))


@router.get("/platforms", response_model=CatalogResponse)
async def list_platforms() -> CatalogResponse:
    """플랫폼 카탈로그 조회 (JSON)."""
    svc = get_catalog_service()
    items = svc.get_json("platforms")
    return CatalogResponse(items=items, total=len(items))


@router.get("/pipelines", response_model=CatalogResponse)
async def list_pipelines() -> CatalogResponse:
    """파이프라인 카탈로그 조회 (JSON)."""
    svc = get_catalog_service()
    items = svc.get_json("pipelines")
    return CatalogResponse(items=items, total=len(items))
