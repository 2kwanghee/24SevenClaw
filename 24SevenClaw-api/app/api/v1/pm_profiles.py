"""PM 프로필 API 라우터 — 5개 엔드포인트."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.pm_profile import (
    PMMetricsResponse,
    PMProfileListResponse,
    PMProfileResponse,
    PMRatingCreate,
    PMRatingResponse,
    PMRecommendListResponse,
    PMRecommendRequest,
    PMRecommendResponse,
)
from app.services.pm_service import PMService

router = APIRouter(prefix="/pm-profiles", tags=["pm-profiles"])


@router.get("/", response_model=PMProfileListResponse)
async def list_profiles(
    domain: str | None = Query(None, max_length=100),
    is_active: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMProfileListResponse:
    """PM 프로필 목록을 반환한다."""
    service = PMService(db)
    profiles, total = await service.list_profiles(
        domain=domain, is_active=is_active, offset=offset, limit=limit
    )
    return PMProfileListResponse(
        items=[PMProfileResponse.model_validate(p) for p in profiles],
        total=total,
    )


@router.get("/{profile_id}", response_model=PMProfileResponse)
async def get_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMProfileResponse:
    """PM 프로필을 조회한다."""
    service = PMService(db)
    profile = await service.get_profile(profile_id)
    return PMProfileResponse.model_validate(profile)


@router.post("/recommend", response_model=PMRecommendListResponse)
async def recommend_pms(
    data: PMRecommendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMRecommendListResponse:
    """프로토타입에 적합한 PM을 추천한다."""
    service = PMService(db)
    recommendations = await service.recommend_pms(data.prototype_id)
    return PMRecommendListResponse(
        items=[
            PMRecommendResponse(
                pm_profile=PMProfileResponse.model_validate(r["pm_profile"]),
                match_score=int(r["match_score"]),
                reasoning=str(r["reasoning"]) if r["reasoning"] else None,
            )
            for r in recommendations
        ]
    )


@router.post(
    "/{profile_id}/rate", response_model=PMRatingResponse
)
async def rate_pm(
    profile_id: UUID,
    data: PMRatingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMRatingResponse:
    """PM을 평가한다."""
    service = PMService(db)
    rating = await service.rate_pm(
        pm_profile_id=profile_id, user_id=user.id, data=data  # type: ignore[arg-type]
    )
    return PMRatingResponse.model_validate(rating)


@router.get(
    "/{profile_id}/metrics", response_model=PMMetricsResponse
)
async def get_metrics(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMMetricsResponse:
    """PM 메트릭을 조회한다."""
    service = PMService(db)
    metric = await service.get_metrics(profile_id)
    return PMMetricsResponse.model_validate(metric)
