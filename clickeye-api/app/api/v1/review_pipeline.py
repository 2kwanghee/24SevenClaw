import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session as db_session_factory
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
    PushToLinearResponse,
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["review-pipeline"])


# === 파이프라인 자동 진행 (BackgroundTask) ===


async def _auto_progress_pipeline(session_id: UUID) -> None:
    """drafting → reviewing → integrating → validating 자동 진행.

    generate_drafts 완료 후 BackgroundTask로 실행된다.
    resume_pipeline 엔드포인트에서도 재호출 가능하다.
    """
    from app.models.orchestrator import OrchestratorSession, PhaseEvent  # noqa: PLC0415
    from app.models.review_pipeline import ReviewRound  # noqa: PLC0415
    from app.schemas.orchestrator import PhaseTransitionRequest  # noqa: PLC0415

    async with db_session_factory() as db:
        orch = OrchestratorService(db)
        review = ReviewPipelineService(db)
        try:
            session = await orch.get_session(session_id)
            current_phase = str(session.phase)

            # 05단계: drafting → reviewing 전이
            if current_phase == "drafting":
                await orch.transition(
                    session_id=session_id,
                    data=PhaseTransitionRequest(
                        target_phase="reviewing", message="자동 교차 리뷰 시작"
                    ),
                    actor_type="system",
                )
                current_phase = "reviewing"

            # 05단계: draft_submitted 라운드마다 교차 리뷰 자동 생성
            if current_phase == "reviewing":
                draft_rows = await db.execute(
                    select(ReviewRound)
                    .where(ReviewRound.session_id == session_id)
                    .where(ReviewRound.status == "draft_submitted")
                )
                for rnd in draft_rows.scalars().all():
                    try:
                        await review.generate_review(rnd.id)  # type: ignore[arg-type]
                    except Exception as exc:
                        logger.error("generate_review 실패 round=%s: %s", rnd.id, exc)

                # reviewing → integrating 전이
                await orch.transition(
                    session_id=session_id,
                    data=PhaseTransitionRequest(
                        target_phase="integrating", message="자동 통합 시작"
                    ),
                    actor_type="system",
                )
                current_phase = "integrating"

            # 06단계: review_completed 라운드마다 draft 그대로 병합
            if current_phase == "integrating":
                completed_rows = await db.execute(
                    select(ReviewRound)
                    .where(ReviewRound.session_id == session_id)
                    .where(ReviewRound.status == "review_completed")
                )
                for rnd in completed_rows.scalars().all():
                    try:
                        await review.merge(rnd.id, MergeRequest(merge_strategy="accept_draft"))  # type: ignore[arg-type]
                    except Exception as exc:
                        logger.error("merge 실패 round=%s: %s", rnd.id, exc)

                # integrating → validating 전이
                await orch.transition(
                    session_id=session_id,
                    data=PhaseTransitionRequest(
                        target_phase="validating", message="자동 검증 단계 진입"
                    ),
                    actor_type="system",
                )

        except Exception as exc:
            logger.error("_auto_progress_pipeline 실패 session=%s: %s", session_id, exc)
            # 오류 PhaseEvent 기록 (사용자에게 가시성 제공)
            try:
                session_obj = await db.get(OrchestratorSession, session_id)
                if session_obj is not None:
                    err_event = PhaseEvent(
                        session_id=session_id,
                        old_phase=str(session_obj.phase),
                        new_phase=str(session_obj.phase),
                        actor_type="system",
                        message=f"자동 파이프라인 오류: {str(exc)[:200]}",
                    )
                    db.add(err_event)
                    await db.commit()
            except Exception:
                pass


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
    background_tasks: BackgroundTasks,
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
        session_description=str(session.description) if session.description else None,
        subtasks=hint_subtasks,
    )

    # 응답 반환 후 백그라운드에서 reviewing → integrating → validating 자동 진행
    background_tasks.add_task(_auto_progress_pipeline, session_id)

    return GenerateDraftsResponse(rounds=rounds, linear_sync_hint=linear_sync_hint)


# === 중단된 파이프라인 재개 ===


@router.post(
    "/sessions/{session_id}/resume-pipeline",
    status_code=status.HTTP_202_ACCEPTED,
)
async def resume_pipeline(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> dict:  # type: ignore[type-arg]
    """중단된 파이프라인을 재개한다 (drafting/reviewing/integrating 단계에서 가능)."""
    orch_service = OrchestratorService(db)
    session = await orch_service.get_session(session_id)

    resumable_phases = {"drafting", "reviewing", "integrating"}
    if session.phase not in resumable_phases:
        raise HTTPException(
            status_code=422,
            detail=(
                f"재개 가능한 단계가 아닙니다. 현재: '{session.phase}' "
                f"(재개 가능: {sorted(resumable_phases)})"
            ),
        )

    background_tasks.add_task(_auto_progress_pipeline, session_id)
    return {"message": "파이프라인 재개를 시작했습니다.", "session_id": str(session_id)}


# === 서버 대행 Linear 이슈 생성 ===


@router.post(
    "/sessions/{session_id}/push-to-linear",
    response_model=PushToLinearResponse,
    status_code=status.HTTP_201_CREATED,
)
async def push_to_linear(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PushToLinearResponse:
    """마지막 generate-drafts 결과를 사용자 Linear에 실제 이슈로 생성한다."""
    from sqlalchemy import select as sa_select

    from app.core.crypto import decrypt
    from app.models.orchestrator import OrchestratorSession, SubTask
    from app.models.project_linear_credentials import ProjectLinearCredentials
    from app.models.user_linear_credentials import UserLinearCredentials
    from app.schemas.review_pipeline import LinearSyncHintSubtask as HintSubtask
    from app.services.linear_service import create_issues, get_queued_state_id

    # 세션 먼저 로드 (project_id를 자격증명 조회에 사용)
    session_result = await db.execute(
        sa_select(OrchestratorSession).where(OrchestratorSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다")

    # 프로젝트별 자격증명 우선, 없으면 유저 전역 자격증명 폴백
    proj_creds_result = await db.execute(
        sa_select(ProjectLinearCredentials).where(
            ProjectLinearCredentials.project_id == session.project_id
        )
    )
    proj_creds = proj_creds_result.scalar_one_or_none()

    if proj_creds is not None:
        api_key = decrypt(str(proj_creds.encrypted_api_key))
        team_id = str(proj_creds.team_id)
    else:
        creds_result = await db.execute(
            sa_select(UserLinearCredentials).where(
                UserLinearCredentials.user_id == user.id
            )
        )
        creds = creds_result.scalar_one_or_none()
        if creds is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Linear 자격증명 미설정. 설정 → Linear에서 API 키를 저장하세요.",
            )
        api_key = decrypt(str(creds.encrypted_api_key))
        team_id = str(creds.team_id)

    # 서브태스크 조회
    subtask_result = await db.execute(
        sa_select(SubTask)
        .where(SubTask.session_id == session_id)
        .order_by(SubTask.order_index)
    )
    subtasks = subtask_result.scalars().all()
    if not subtasks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="서브태스크가 없습니다. 먼저 AI 초안 생성을 실행하세요.",
        )

    hint_subtasks = [
        HintSubtask(
            title=str(st.title),
            role=str(st.assigned_role or "AI"),
            draft_summary=str(st.result_summary or st.description or ""),
        )
        for st in subtasks
    ]

    # Queued 상태 ID 조회 (실패 시 None — 이슈는 정상 생성, 상태만 미적용)
    queued_state_id = get_queued_state_id(api_key, team_id)

    created = create_issues(
        api_key,
        team_id,
        hint_subtasks,
        state_id=queued_state_id,
        session_description=str(session.description) if session.description else None,
    )

    return PushToLinearResponse(
        created_identifiers=[c["identifier"] for c in created],
        created_urls=[c["url"] for c in created],
        count=len(created),
        queued_state_applied=queued_state_id is not None,
    )


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
