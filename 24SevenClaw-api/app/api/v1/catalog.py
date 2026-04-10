"""카탈로그 조회 엔드포인트 (agents, skills, platforms, pipelines)."""

from fastapi import APIRouter

from app.schemas.catalog import CatalogResponse
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])

_service = CatalogService()


@router.get("/agents", response_model=CatalogResponse)
async def list_agents() -> CatalogResponse:
    """에이전트 카탈로그 조회."""
    items = _service.get("agents")
    return CatalogResponse(items=items, total=len(items))


@router.get("/skills", response_model=CatalogResponse)
async def list_skills() -> CatalogResponse:
    """스킬 카탈로그 조회 (워크플로우 + 외부 도구)."""
    items = _service.get("skills")
    return CatalogResponse(items=items, total=len(items))


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
