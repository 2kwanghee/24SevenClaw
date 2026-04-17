from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.orchestrator import SubTask
from app.models.user import User
from app.schemas.review_pipeline import (
    DiffResult,
    GenerateDraftsResponse,
    LinearSyncHint,
    LinearSyncHintSubtask,
    MergeRequest,
    RejectRequest,
    ReviewEventResponse,
    ReviewPrompt,
    ReviewRoundCreate,
    ReviewRoundListResponse,
    ReviewRoundResponse,
    ReviewSubmit,
)
from app.services.claude_service import ClaudeService
from app.services.orchestrator_service import OrchestratorService
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


# === AI 초안 자동 생성 ===


@router.post(
    "/sessions/{session_id}/generate-drafts",
    response_model=GenerateDraftsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_drafts(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> GenerateDraftsResponse:
    """서브태스크별 AI 초안을 자동 생성하고 drafting 단계로 전이한다."""
    orch_service = OrchestratorService(db)
    review_service = ReviewPipelineService(db)
    claude = ClaudeService()

    session = await orch_service.get_session(session_id)
    if session.phase != "assigned":
        raise HTTPException(
            status_code=422,
            detail=f"AI 초안 생성은 'assigned' 단계에서만 가능합니다. 현재: '{session.phase}'",
        )

    # 서브태스크 조회
    result = await db.execute(
        select(SubTask)
        .where(SubTask.session_id == session_id)
        .order_by(SubTask.order_index)
    )
    subtasks = list(result.scalars().all())

    if not subtasks:
        raise HTTPException(status_code=422, detail="분해된 서브태스크가 없습니다.")

    # drafting 단계로 전이
    from app.schemas.orchestrator import PhaseTransitionRequest  # noqa: PLC0415
    await orch_service.transition(
        session_id=session_id,
        data=PhaseTransitionRequest(target_phase="drafting", message="AI 초안 생성 시작"),
        actor_type="system",
    )

    session_context = f"세션: {session.title}\n설명: {session.description or '없음'}"

    rounds = []
    for st in subtasks:
        draft_content = await claude.generate_draft(
            subtask_title=str(st.title),
            subtask_description=str(st.description) if st.description else None,
            session_context=session_context,
        )
        review_round = await review_service.submit_draft(
            session_id=session_id,
            data=ReviewRoundCreate(
                subtask_id=st.id,
                main_ai_role=str(st.assigned_role),
                draft_content=draft_content,
            ),
        )
        rounds.append(ReviewRoundResponse.model_validate(review_round))

    # LinearSyncHint 생성
    hint_subtasks = [
        LinearSyncHintSubtask(
            title=str(st.title),
            role=str(st.assigned_role),
            draft_summary=(
                r.draft_content[:200] + "..." if len(r.draft_content) > 200 else r.draft_content
            ),
        )
        for st, r in zip(subtasks, rounds, strict=False)
    ]
    linear_sync_hint = LinearSyncHint(
        session_title=str(session.title),
        subtasks=hint_subtasks,
    )

    return GenerateDraftsResponse(rounds=rounds, linear_sync_hint=linear_sync_hint)


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
