from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.review_pipeline import (
    DiffResult,
    MergeRequest,
    RejectRequest,
    ReviewEventResponse,
    ReviewPrompt,
    ReviewRoundCreate,
    ReviewRoundListResponse,
    ReviewRoundResponse,
    ReviewSubmit,
)
from app.services.review_pipeline import ReviewPipelineService

router = APIRouter(prefix="/orchestrator", tags=["review-pipeline"])


# === 초안 제출 ===


@router.post(
    "/sessions/{session_id}/reviews",
    response_model=ReviewRoundResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_draft(
    session_id: UUID,
    data: ReviewRoundCreate,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ReviewRoundResponse:
    """메인 AI 초안을 제출하고 교차 리뷰 라운드를 생성한다."""
    service = ReviewPipelineService(db)
    review_round = await service.submit_draft(session_id=session_id, data=data)
    return ReviewRoundResponse.model_validate(review_round)


# === 리뷰 라운드 조회 ===


@router.get(
    "/sessions/{session_id}/reviews",
    response_model=ReviewRoundListResponse,
)
async def list_review_rounds(
    session_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ReviewRoundListResponse:
    """세션의 교차 리뷰 라운드 목록을 조회한다."""
    service = ReviewPipelineService(db)
    rounds, total = await service.list_rounds(
        session_id=session_id, offset=offset, limit=limit
    )
    return ReviewRoundListResponse(
        items=[ReviewRoundResponse.model_validate(r) for r in rounds],
        total=total,
    )


@router.get(
    "/reviews/{round_id}",
    response_model=ReviewRoundResponse,
)
async def get_review_round(
    round_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ReviewRoundResponse:
    """리뷰 라운드 상세 조회."""
    service = ReviewPipelineService(db)
    review_round = await service.get_round(round_id)
    return ReviewRoundResponse.model_validate(review_round)


# === 교차 리뷰 제출 ===


@router.post(
    "/reviews/{round_id}/review",
    response_model=ReviewRoundResponse,
)
async def submit_review(
    round_id: UUID,
    data: ReviewSubmit,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ReviewRoundResponse:
    """서브 AI 교차 리뷰를 제출한다."""
    service = ReviewPipelineService(db)
    review_round = await service.submit_review(round_id=round_id, data=data)
    return ReviewRoundResponse.model_validate(review_round)


# === diff 조회 ===


@router.get(
    "/reviews/{round_id}/diff",
    response_model=DiffResult,
)
async def get_diff(
    round_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> DiffResult:
    """리뷰 라운드의 draft↔review diff를 조회한다."""
    service = ReviewPipelineService(db)
    review_round = await service.get_diff(round_id)
    return DiffResult(
        round_id=review_round.id,
        draft_content=review_round.draft_content,
        review_content=review_round.review_content or "",
        diff_summary=review_round.diff_summary or "",
        review_type=review_round.review_type,
    )


# === 병합 ===


@router.post(
    "/reviews/{round_id}/merge",
    response_model=ReviewRoundResponse,
)
async def merge_review(
    round_id: UUID,
    data: MergeRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ReviewRoundResponse:
    """리뷰 결과를 병합한다 (06단계: integrating)."""
    service = ReviewPipelineService(db)
    review_round = await service.merge(round_id=round_id, data=data)
    return ReviewRoundResponse.model_validate(review_round)


# === 거절 ===


@router.post(
    "/reviews/{round_id}/reject",
    response_model=ReviewRoundResponse,
)
async def reject_review(
    round_id: UUID,
    data: RejectRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ReviewRoundResponse:
    """리뷰 결과를 거절하고 재작성을 요청한다."""
    service = ReviewPipelineService(db)
    review_round = await service.reject(round_id=round_id, reason=data.reason)
    return ReviewRoundResponse.model_validate(review_round)


# === 이벤트 이력 ===


@router.get(
    "/reviews/{round_id}/events",
    response_model=list[ReviewEventResponse],
)
async def get_review_events(
    round_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> list[ReviewEventResponse]:
    """리뷰 라운드의 이벤트 이력을 조회한다."""
    service = ReviewPipelineService(db)
    events = await service.get_events(round_id)
    return [ReviewEventResponse.model_validate(e) for e in events]


# === 프롬프트 생성 ===


@router.get(
    "/reviews/{round_id}/prompt",
    response_model=ReviewPrompt,
)
async def get_review_prompt(
    round_id: UUID,
    review_type: str = Query("cross_review"),
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> ReviewPrompt:
    """교차 리뷰용 표준 프롬프트를 생성한다."""
    service = ReviewPipelineService(db)
    return await service.build_review_prompt(round_id=round_id, review_type=review_type)
