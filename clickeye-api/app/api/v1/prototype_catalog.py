"""프로토타입 카탈로그 공개 API — 위저드에서 태그/엔트리 조회."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.prototype_catalog import (
    PrototypeCatalogEntryResponse,
    PrototypeCatalogListResponse,
    PrototypeTagListResponse,
    PrototypeTagResponse,
)
from app.services.prototype_catalog_service import PrototypeCatalogService

router = APIRouter(tags=["prototype-catalog"])


@router.get("/prototype-catalog", response_model=PrototypeCatalogListResponse)
async def list_catalog_entries(
    primary_tag: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeCatalogListResponse:
    """활성 카탈로그 엔트리 목록. 위저드에서 프로토타입 선택지 표시에 사용."""
    svc = PrototypeCatalogService(db)
    items, total = await svc.list_entries(
        primary_tag=primary_tag, is_active=True, offset=offset, limit=limit
    )
    return PrototypeCatalogListResponse(
        items=[PrototypeCatalogEntryResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/prototype-tags", response_model=PrototypeTagListResponse)
async def list_tags(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PrototypeTagListResponse:
    """활성 태그 목록. 위저드 필터 및 카탈로그 엔트리 분류에 사용."""
    svc = PrototypeCatalogService(db)
    items, total = await svc.list_tags(is_active=True)
    return PrototypeTagListResponse(
        items=[PrototypeTagResponse.model_validate(i) for i in items],
        total=total,
    )
