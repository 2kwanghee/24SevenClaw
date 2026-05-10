"""전역 앱 설정 관리 API — admin/superadmin 전용."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.app_setting import (
    AppSettingResponse,
    VariantCountUpdateRequest,
)
from app.services.app_setting_service import AppSettingService

router = APIRouter(
    prefix="/admin/settings",
    tags=["admin-settings"],
    dependencies=[Depends(require_permission("settings:manage"))],
)


@router.get("", response_model=list[AppSettingResponse])
async def list_settings(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AppSettingResponse]:
    """전체 앱 설정 목록 조회."""
    svc = AppSettingService(db)
    items = await svc.get_all()
    return [AppSettingResponse.model_validate(i) for i in items]


@router.put("/prototype-variant-count", response_model=AppSettingResponse)
async def update_variant_count(
    data: VariantCountUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppSettingResponse:
    """프로토타입 제안 개수 설정 (2-5, 기본 3)."""
    svc = AppSettingService(db)
    row = await svc.set_variant_count(data.value, user)
    return AppSettingResponse.model_validate(row)


@router.put("/prototype-rag-top-k", response_model=AppSettingResponse)
async def update_rag_top_k(
    data: VariantCountUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AppSettingResponse:
    """Claude 카탈로그 참조 top-k 설정 (1-20, 기본 8)."""
    svc = AppSettingService(db)
    row = await svc.set_rag_top_k(data.value, user)
    return AppSettingResponse.model_validate(row)


