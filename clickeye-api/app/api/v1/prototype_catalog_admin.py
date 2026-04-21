"""프로토타입 카탈로그 Admin API — 카탈로그 엔트리 및 태그 CRUD."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.prototype_catalog import (
    PrototypeCatalogEntryCreate,
    PrototypeCatalogEntryResponse,
    PrototypeCatalogEntryUpdate,
    PrototypeCatalogListResponse,
    PrototypeTagCreate,
    PrototypeTagListResponse,
    PrototypeTagResponse,
    PrototypeTagUpdate,
)
from app.services.prototype_catalog_service import PrototypeCatalogService

router = APIRouter(prefix="/admin/registry", tags=["admin-prototype-catalog"])


# ── Catalog Entries ───────────────────────────────────────────────────────────

@router.get("/prototype-catalog", response_model=PrototypeCatalogListResponse)
async def list_catalog_entries(
    primary_tag: str | None = Query(None),
    is_active: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeCatalogListResponse:
    svc = PrototypeCatalogService(db)
    items, total = await svc.list_entries(
        primary_tag=primary_tag, is_active=is_active, offset=offset, limit=limit
    )
    return PrototypeCatalogListResponse(
        items=[PrototypeCatalogEntryResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post(
    "/prototype-catalog",
    response_model=PrototypeCatalogEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_catalog_entry(
    data: PrototypeCatalogEntryCreate,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeCatalogEntryResponse:
    svc = PrototypeCatalogService(db)
    item = await svc.create_entry(data)
    return PrototypeCatalogEntryResponse.model_validate(item)


@router.get("/prototype-catalog/{entry_id}", response_model=PrototypeCatalogEntryResponse)
async def get_catalog_entry(
    entry_id: UUID,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeCatalogEntryResponse:
    svc = PrototypeCatalogService(db)
    item = await svc.get_entry(entry_id)
    return PrototypeCatalogEntryResponse.model_validate(item)


@router.put("/prototype-catalog/{entry_id}", response_model=PrototypeCatalogEntryResponse)
async def update_catalog_entry(
    entry_id: UUID,
    data: PrototypeCatalogEntryUpdate,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeCatalogEntryResponse:
    svc = PrototypeCatalogService(db)
    item = await svc.update_entry(entry_id, data)
    return PrototypeCatalogEntryResponse.model_validate(item)


@router.delete("/prototype-catalog/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_catalog_entry(
    entry_id: UUID,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = PrototypeCatalogService(db)
    await svc.delete_entry(entry_id)


# ── Prototype Tags ────────────────────────────────────────────────────────────

@router.get("/prototype-tags", response_model=PrototypeTagListResponse)
async def list_tags(
    is_active: bool | None = Query(None),
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeTagListResponse:
    svc = PrototypeCatalogService(db)
    items, total = await svc.list_tags(is_active=is_active)
    return PrototypeTagListResponse(
        items=[PrototypeTagResponse.model_validate(i) for i in items],
        total=total,
    )


@router.post(
    "/prototype-tags",
    response_model=PrototypeTagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_tag(
    data: PrototypeTagCreate,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeTagResponse:
    svc = PrototypeCatalogService(db)
    tag = await svc.create_tag(data)
    return PrototypeTagResponse.model_validate(tag)


@router.get("/prototype-tags/{tag_id}", response_model=PrototypeTagResponse)
async def get_tag(
    tag_id: UUID,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeTagResponse:
    svc = PrototypeCatalogService(db)
    tag = await svc.get_tag(tag_id)
    return PrototypeTagResponse.model_validate(tag)


@router.put("/prototype-tags/{tag_id}", response_model=PrototypeTagResponse)
async def update_tag(
    tag_id: UUID,
    data: PrototypeTagUpdate,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> PrototypeTagResponse:
    svc = PrototypeCatalogService(db)
    tag = await svc.update_tag(tag_id, data)
    return PrototypeTagResponse.model_validate(tag)


@router.delete("/prototype-tags/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    user: User = Depends(require_permission("prototype:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = PrototypeCatalogService(db)
    await svc.delete_tag(tag_id)
