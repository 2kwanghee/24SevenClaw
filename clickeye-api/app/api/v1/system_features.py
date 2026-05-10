"""시스템 기능 플래그 API — 인증된 사용자 누구나 읽기 가능."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.app_setting_service import AppSettingService

router = APIRouter(prefix="/system", tags=["system"])


class SystemFeaturesResponse(BaseModel):
    live_preview_enabled: bool


@router.get("/features", response_model=SystemFeaturesResponse)
async def get_system_features(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SystemFeaturesResponse:
    """현재 활성화된 시스템 기능 플래그를 반환한다."""
    svc = AppSettingService(db)
    return SystemFeaturesResponse(
        live_preview_enabled=await svc.get_live_preview_enabled(),
    )
