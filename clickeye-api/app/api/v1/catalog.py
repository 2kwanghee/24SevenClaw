"""카탈로그 조회 엔드포인트 (agents, skills, platforms, pipelines)."""

from fastapi import APIRouter

from app.schemas.catalog import CatalogListResponse, CatalogResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])

_service = CatalogService()


@router.get("/agents", response_model=CatalogListResponse)
async def list_agents() -> CatalogListResponse:
    """에이전트 카탈로그 조회 (id, label, description 반환)."""
    items = _service.get("agents")
    return CatalogListResponse(items=items, total=len(items))


@router.get("/skills", response_model=CatalogListResponse)
async def list_skills() -> CatalogListResponse:
    """스킬 카탈로그 조회 (id, label, description 반환)."""
    items = _service.get("skills")
    return CatalogListResponse(items=items, total=len(items))


@router.get("/platforms", response_model=CatalogResponse)
async def list_platforms() -> CatalogResponse:
    """플랫폼 카탈로그 조회."""
    items = _service.get("platforms")
    return CatalogResponse(items=items, total=len(items))


@router.get("/pipelines", response_model=CatalogResponse)
async def list_pipelines() -> CatalogResponse:
    """파이프라인 카탈로그 조회."""
    items = _service.get("pipelines")
    return CatalogResponse(items=items, total=len(items))
