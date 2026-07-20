"""PM 프로필 API 라우터."""

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.pm_profile import (
    PMCompositionCreate,
    PMCompositionGroupedResponse,
    PMCompositionResponse,
    PMCompositionUpdate,
    PMMetricsResponse,
    PMProfileCreate,
    PMProfileListResponse,
    PMProfileResponse,
    PMProfileUpdate,
    PMProfileWithMetrics,
    PMRatingCreate,
    PMRatingListResponse,
    PMRatingResponse,
    PMRecommendListResponse,
    PMRecommendRequest,
    PMRecommendResponse,
)
from app.services.pm_markdown_service import parse_markdown_to_pm_dict, serialize_pm_to_markdown
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


@router.get("/{profile_id}/composition", response_model=PMCompositionGroupedResponse)
async def get_composition(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMCompositionGroupedResponse:
    """PM 구성 컴포넌트를 타입별로 그룹화하여 반환한다."""
    service = PMService(db)
    return await service.get_composition(profile_id)


@router.post("/{profile_id}/ratings", response_model=PMRatingResponse, status_code=201)
async def rate_pm(
    profile_id: UUID,
    data: PMRatingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMRatingResponse:
    """PM을 평가한다."""
    service = PMService(db)
    rating = await service.rate_pm(
        pm_profile_id=profile_id,
        user_id=user.id,  # type: ignore[arg-type]  # TODO: 타입 정합
        data=data,
    )
    return PMRatingResponse.model_validate(rating)


@router.get("/{profile_id}/ratings", response_model=PMRatingListResponse)
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


@router.get("/{profile_id}/metrics", response_model=PMMetricsResponse)
async def get_metrics(
    profile_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PMMetricsResponse:
    """PM 메트릭을 조회한다."""
    service = PMService(db)
    metric = await service.get_metrics(profile_id)
    return PMMetricsResponse.model_validate(metric)


# ── Admin 전용 엔드포인트 (pm:manage 권한 필요) ──────────────────────────────


@router.post("/", response_model=PMProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: PMProfileCreate,
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> PMProfileResponse:
    """PM 프로필을 생성한다. (관리자 전용)"""
    service = PMService(db)
    profile = await service.create_profile(data)
    return PMProfileResponse.model_validate(profile)


@router.put("/{profile_id}", response_model=PMProfileResponse)
async def update_profile(
    profile_id: UUID,
    data: PMProfileUpdate,
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> PMProfileResponse:
    """PM 프로필을 수정한다. (관리자 전용)"""
    service = PMService(db)
    profile = await service.update_profile(profile_id, data)
    return PMProfileResponse.model_validate(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: UUID,
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """PM 프로필을 삭제한다. (관리자 전용)"""
    service = PMService(db)
    await service.delete_profile(profile_id)


@router.post(
    "/{profile_id}/composition",
    response_model=PMCompositionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_composition(
    profile_id: UUID,
    data: PMCompositionCreate,
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> PMCompositionResponse:
    """PM 구성 컴포넌트를 추가한다. (관리자 전용)"""
    service = PMService(db)
    composition = await service.create_composition(profile_id, data)
    return PMCompositionResponse.model_validate(composition)


@router.put(
    "/{profile_id}/composition/{composition_id}",
    response_model=PMCompositionResponse,
)
async def update_composition(
    profile_id: UUID,
    composition_id: UUID,
    data: PMCompositionUpdate,
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> PMCompositionResponse:
    """PM 구성 컴포넌트를 수정한다. (관리자 전용)"""
    service = PMService(db)
    composition = await service.update_composition(composition_id, data)
    return PMCompositionResponse.model_validate(composition)


@router.delete(
    "/{profile_id}/composition/{composition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_composition(
    profile_id: UUID,
    composition_id: UUID,
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """PM 구성 컴포넌트를 삭제한다. (관리자 전용)"""
    service = PMService(db)
    await service.delete_composition(composition_id)


# ── Markdown 양방향 편집 ──────────────────────────────────────────────────────


@router.get(
    "/{profile_id}/markdown",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {}}}},
)
async def get_profile_markdown(
    profile_id: UUID,
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> str:
    """PM 프로필을 Markdown(YAML frontmatter + 본문) 형식으로 반환한다. (관리자 전용)"""
    from fastapi import HTTPException

    from app.models.pm_profile import PMProfile as _PMModel

    profile = await db.get(_PMModel, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="PM 프로필을 찾을 수 없습니다")
    return serialize_pm_to_markdown(profile)


@router.put(
    "/{profile_id}/markdown",
    response_model=PMProfileResponse,
)
async def update_profile_from_markdown(
    profile_id: UUID,
    markdown: str = Body(..., media_type="text/plain"),
    user: User = Depends(require_permission("pm:manage")),
    db: AsyncSession = Depends(get_db),
) -> PMProfileResponse:
    """Markdown 텍스트를 파싱하여 PM 프로필을 업데이트한다. (관리자 전용)"""
    update_dict = parse_markdown_to_pm_dict(markdown)
    # slug는 URL 기반 식별자이므로 변경 방지
    update_dict.pop("slug", None)
    # 원본 Markdown 본문을 저장한다
    update_dict["markdown_body"] = markdown
    data = PMProfileUpdate(**update_dict)
    service = PMService(db)
    profile = await service.update_profile(profile_id, data)
    return PMProfileResponse.model_validate(profile)
