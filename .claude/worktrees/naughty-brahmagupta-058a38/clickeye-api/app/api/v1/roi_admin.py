"""ROI 표준 단가/공수 관리 API — 관리자 전용."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.roi_standard import RoiCategory
from app.models.user import User
from app.schemas.roi import (
    RoiStandardCreate,
    RoiStandardListResponse,
    RoiStandardResponse,
    RoiStandardUpdate,
)
from app.services.roi_service import RoiService

router = APIRouter(prefix="/admin/roi-standards", tags=["admin-roi"])


@router.get("", response_model=RoiStandardListResponse)
async def list_roi_standards(
    category: RoiCategory | None = Query(None),
    include_inactive: bool = Query(False),
    user: User = Depends(require_permission("settings:manage")),
    db: AsyncSession = Depends(get_db),
) -> RoiStandardListResponse:
    svc = RoiService(db)
    if include_inactive:
        items = await svc.list_standards_all(category)
    else:
        items = await svc.list_standards(category)
    return RoiStandardListResponse(
        items=[RoiStandardResponse.model_validate(i) for i in items],
        total=len(items),
    )


@router.post("", response_model=RoiStandardResponse, status_code=status.HTTP_201_CREATED)
async def create_roi_standard(
    data: RoiStandardCreate,
    user: User = Depends(require_permission("settings:manage")),
    db: AsyncSession = Depends(get_db),
) -> RoiStandardResponse:
    svc = RoiService(db)
    item = await svc.create_standard(data, updated_by=user.id)
    return RoiStandardResponse.model_validate(item)


@router.put("/{standard_id}", response_model=RoiStandardResponse)
async def update_roi_standard(
    standard_id: UUID,
    data: RoiStandardUpdate,
    user: User = Depends(require_permission("settings:manage")),
    db: AsyncSession = Depends(get_db),
) -> RoiStandardResponse:
    svc = RoiService(db)
    item = await svc.update_standard(standard_id, data, updated_by=user.id)
    return RoiStandardResponse.model_validate(item)


@router.delete("/{standard_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roi_standard(
    standard_id: UUID,
    user: User = Depends(require_permission("settings:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    svc = RoiService(db)
    await svc.delete_standard(standard_id)
