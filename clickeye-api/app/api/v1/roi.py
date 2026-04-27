"""ROI 계산 API — 인증된 사용자 대상."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.roi import RoiCalculateRequest, RoiCalculateResponse
from app.services.roi_service import RoiService

router = APIRouter(prefix="/roi", tags=["roi"])


@router.post("/calculate", response_model=RoiCalculateResponse)
async def calculate_roi(
    data: RoiCalculateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RoiCalculateResponse:
    svc = RoiService(db)
    return await svc.calculate(data)
