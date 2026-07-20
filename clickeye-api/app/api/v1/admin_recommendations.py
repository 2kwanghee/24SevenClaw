"""PM 추천 로그 관리자 API."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.pm_recommendation_log import PMRecommendationLog
from app.models.user import User
from app.schemas.pm_profile import PMRecommendationLogListResponse, PMRecommendationLogResponse

router = APIRouter(prefix="/admin/pm-recommendations", tags=["admin-pm-recommendations"])


@router.get("/", response_model=PMRecommendationLogListResponse)
async def list_recommendation_logs(
    session_id: UUID | None = Query(None),
    is_fallback: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> PMRecommendationLogListResponse:
    """PM 추천 로그 목록을 반환한다. (관리자 전용)"""
    conditions = []
    if session_id is not None:
        conditions.append(PMRecommendationLog.session_id == session_id)
    if is_fallback is not None:
        conditions.append(PMRecommendationLog.is_fallback == is_fallback)

    count_stmt = select(func.count()).select_from(PMRecommendationLog).where(*conditions)
    total_result = await db.execute(count_stmt)
    total = int(total_result.scalar_one())

    stmt = (
        select(PMRecommendationLog)
        .where(*conditions)
        .order_by(PMRecommendationLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    logs = list(result.scalars().all())

    return PMRecommendationLogListResponse(
        items=[PMRecommendationLogResponse.model_validate(log) for log in logs],
        total=total,
    )
