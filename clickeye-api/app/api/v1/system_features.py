"""시스템 기능 플래그 API — 인증된 사용자 누구나 읽기 가능."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/system", tags=["system"])


class SystemFeaturesResponse(BaseModel):
    live_preview_enabled: bool


@router.get("/features", response_model=SystemFeaturesResponse)
async def get_system_features(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SystemFeaturesResponse:
    """현재 사용자 조직의 기능 플래그를 반환한다."""
    live_preview = False
    if user.organization_id:
        org = await db.get(Organization, user.organization_id)
        if org:
            live_preview = bool((org.features or {}).get("live_preview_enabled", False))  # type: ignore[call-overload]  # TODO: 타입 정합
    return SystemFeaturesResponse(live_preview_enabled=live_preview)
