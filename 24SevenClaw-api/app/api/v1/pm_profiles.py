"""PM 프로필 API 라우터."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.pm_profile import (
    PMCompositionGroupedResponse,
    PMMetricsResponse,
    PMProfileListResponse,
    PMProfileResponse,
    PMProfileWithMetrics,
    PMRatingCreate,
    PMRatingListResponse,
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
    specialty: str | None = Query(None, max_length=100),
    is_active: bool | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMProfileListResponse:
    """PM 프로필 목록을 반환한다."""
    service = PMService(db)
    profiles, total = await service.list_profiles(
        domain=domain,
        specialty=specialty,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return PMProfileListResponse(
        items=[PMProfileResponse.model_validate(p) for p in profiles],
        total=total,
    )


@router.get("/{profile_id}", response_model=PMProfileWithMetrics)
async def get_profile(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMProfileWithMetrics:
    """PM 프로필과 메트릭을 함께 조회한다."""
    service = PMService(db)
    return await service.get_profile(profile_id)


@router.post("/recommend", response_model=PMRecommendListResponse)
async def recommend_pms(
    data: PMRecommendRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMRecommendListResponse:
    """프로토타입에 적합한 PM을 추천한다 (상위 3~5개)."""
    service = PMService(db)
    recommendations = await service.recommend_pms(
        prototype_id=data.prototype_id,
        session_id=data.session_id,
    )
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


@router.get(
    "/{profile_id}/composition", response_model=PMCompositionGroupedResponse
)
async def get_composition(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMCompositionGroupedResponse:
    """PM 구성 컴포넌트를 타입별로 그룹화하여 반환한다."""
    service = PMService(db)
    return await service.get_composition(profile_id)


@router.post(
    "/{profile_id}/ratings", response_model=PMRatingResponse, status_code=201
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
    "/{profile_id}/ratings", response_model=PMRatingListResponse
)
async def list_ratings(
    profile_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMRatingListResponse:
    """PM 평가 목록을 반환한다."""
    service = PMService(db)
    ratings, total = await service.list_ratings(
        pm_profile_id=profile_id, offset=offset, limit=limit
    )
    return PMRatingListResponse(
        items=[PMRatingResponse.model_validate(r) for r in ratings],
        total=total,
    )


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
