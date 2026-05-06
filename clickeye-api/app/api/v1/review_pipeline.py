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
    ApproveSubtaskResponse,
    DiffResult,
    GenerateDraftsResponse,
    LinearSyncHint,
    LinearSyncHintSubtask,
    LinearTeamState,
    LinearTeamStatesResponse,
    MergeRequest,
    PushToLinearResponse,
    RejectRequest,
    ResetToWaitResponse,
    ReviewEventResponse,
    ReviewPrompt,
    ReviewRoundCreate,
    ReviewRoundListResponse,
    ReviewRoundResponse,
    ReviewSubmit,
    SyncedSubtask,
    SyncLinearStatesResponse,
)
from app.services.orchestrator_service import OrchestratorService
from app.services.review_pipeline import ReviewPipelineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orchestrator", tags=["review-pipeline"])


# === 자격증명 헬퍼 ===


from dataclasses import dataclass  # noqa: E402


@dataclass
class _LinearCreds:
    api_key: str
    team_id: str


async def _resolve_linear_credentials(db: AsyncSession, session_id: UUID) -> _LinearCreds | None:
    """세션 ID → project_id → Linear 자격증명을 조회한다.

    ProjectLinearCredentials 우선, 없으면 UserLinearCredentials(세션 생성자) 폴백.
    자격증명이 전혀 없으면 None을 반환한다.
    """
    from sqlalchemy import select as sa_select  # noqa: PLC0415

    from app.core.crypto import decrypt  # noqa: PLC0415
    from app.models.orchestrator import OrchestratorSession  # noqa: PLC0415
    from app.models.project_linear_credentials import ProjectLinearCredentials  # noqa: PLC0415
    from app.models.user_linear_credentials import UserLinearCredentials  # noqa: PLC0415

    sess_result = await db.execute(
        sa_select(OrchestratorSession).where(OrchestratorSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        return None

    proj_result = await db.execute(
        sa_select(ProjectLinearCredentials).where(
            ProjectLinearCredentials.project_id == session.project_id
        )
    )
    proj_creds = proj_result.scalar_one_or_none()
    if proj_creds is not None:
        return _LinearCreds(
            api_key=decrypt(str(proj_creds.encrypted_api_key)),
            team_id=str(proj_creds.team_id),
        )

    user_result = await db.execute(
        sa_select(UserLinearCredentials).where(
            UserLinearCredentials.user_id == session.created_by
        )
    )
    user_creds = user_result.scalar_one_or_none()
    if user_creds is None:
        return None
    return _LinearCreds(
        api_key=decrypt(str(user_creds.encrypted_api_key)),
        team_id=str(user_creds.team_id),
    )


# === 부트스트랩 완료 헬퍼 ===


async def _maybe_complete_bootstrap(
    db: AsyncSession,
    session_id: UUID,
    background_tasks: BackgroundTasks,
) -> None:
    """모든 서브태스크가 approved 상태가 되면 부트스트랩을 completed로 전환한다.

    bootstrap_status="pending_review"인 프로젝트에만 동작한다.
    """
    from datetime import UTC  # noqa: PLC0415
    from datetime import datetime as dt  # noqa: PLC0415

    from sqlalchemy import select as sa_select  # noqa: PLC0415

    from app.api.v1.orchestrator import _auto_complete_pipeline  # noqa: PLC0415
    from app.models.orchestrator import OrchestratorSession  # noqa: PLC0415
    from app.models.orchestrator import SubTask as _SubTask  # noqa: PLC0415
    from app.models.project import Project  # noqa: PLC0415

    all_st_result = await db.execute(
        sa_select(_SubTask).where(_SubTask.session_id == session_id)
    )
    all_sts = all_st_result.scalars().all()
    if not all_sts or any(s.status != "approved" for s in all_sts):
        return

    sess_result = await db.execute(
        sa_select(OrchestratorSession).where(OrchestratorSession.id == session_id)
    )
    sess = sess_result.scalar_one_or_none()
    if sess is None:
        return

    proj_result = await db.execute(
        sa_select(Project).where(Project.id == sess.project_id)
    )
    proj = proj_result.scalar_one_or_none()
    if proj is None or proj.bootstrap_status != "pending_review":
        return

    proj.bootstrap_status = "completed"  # type: ignore[assignment]
    proj.bootstrap_completed_at = dt.now(UTC)  # type: ignore[assignment]
    proj.setup_token_hash = None  # type: ignore[assignment]
    sess.phase = "approved"  # type: ignore[assignment]
    await db.commit()
    background_tasks.add_task(_auto_complete_pipeline, session_id)


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

    rounds = []
    for st in subtasks:
        # 웹 파이프라인은 계획/조율 레이어 — 실제 구현은 로컬 Claude Code 파이프라인에서 처리
        draft_content = (
            f"[웹 파이프라인 자동 초안] {str(st.title)}\n\n"
            f"역할: {str(st.assigned_role)}\n"
            f"세션: {str(session.title)}\n"
            f"설명: {str(session.description or '없음')}\n\n"
            "이 초안은 Linear 이슈 생성용 플레이스홀더입니다.\n"
            "실제 코드 작성 및 구현은 로컬 Claude Code 파이프라인이 담당합니다."
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
    from app.services.linear_service import create_issues, get_initial_state_id

    # 세션 먼저 로드 (project_id를 자격증명 조회에 사용)
    session_result = await db.execute(
        sa_select(OrchestratorSession).where(OrchestratorSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다")

    # 프로젝트별 자격증명 조회, 없으면 사용자 자격증명으로 폴백
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
        user_creds_result = await db.execute(
            sa_select(UserLinearCredentials).where(
                UserLinearCredentials.user_id == session.created_by
            )
        )
        user_creds = user_creds_result.scalar_one_or_none()
        if user_creds is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Linear 자격증명이 설정되지 않았습니다. 설정 → Linear에서 API 키와 Team ID를 입력하세요.",
            )
        api_key = decrypt(str(user_creds.encrypted_api_key))
        team_id = str(user_creds.team_id)

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

    # Wait 상태 ID 조회 (실패 시 None — 이슈는 정상 생성, 상태만 미적용)
    initial_state_id = get_initial_state_id(api_key, team_id)

    created = create_issues(
        api_key,
        team_id,
        hint_subtasks,
        state_id=initial_state_id,
        session_description=str(session.description) if session.description else None,
    )

    # 생성된 Linear 이슈 정보를 subtask 행에 저장
    from datetime import UTC
    from datetime import datetime as dt
    for subtask, issue in zip(subtasks, created, strict=False):
        subtask.linear_identifier = issue.get("identifier") or None
        subtask.linear_issue_id = issue.get("id") or None
        subtask.linear_state = "Backlog" if initial_state_id else None
        subtask.updated_at = dt.now(UTC)
    await db.commit()

    return PushToLinearResponse(
        created_identifiers=[c["identifier"] for c in created],
        created_urls=[c["url"] for c in created],
        count=len(created),
        initial_state_applied=initial_state_id is not None,
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


# === Linear 이슈 상태 전이 ===


@router.post(
    "/sessions/{session_id}/subtasks/{subtask_id}/approve",
    response_model=ApproveSubtaskResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_subtask(
    session_id: UUID,
    subtask_id: UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApproveSubtaskResponse:
    """subtask의 Linear 이슈를 Backlog → Todo로 전이한다 (사람 검수 완료).

    로컬 webhook_server / linear_watcher가 Todo 감지 후 자동으로
    In Progress로 전이하고 Claude 구현을 시작한다.
    """
    from datetime import UTC
    from datetime import datetime as dt

    from sqlalchemy import select as sa_select

    from app.models.orchestrator import OrchestratorSession, SubTask
    from app.services.linear_service import get_queued_state_id, update_issue_state_id

    # subtask 조회 + 세션 소유권 확인
    st_result = await db.execute(
        sa_select(SubTask).where(
            SubTask.id == subtask_id,
            SubTask.session_id == session_id,
        )
    )
    subtask = st_result.scalar_one_or_none()
    if subtask is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="서브태스크를 찾을 수 없습니다")

    if not subtask.linear_issue_id:
        # Linear 자격증명이 있으면 즉시 이슈 생성, 없으면 단순 승인
        creds = await _resolve_linear_credentials(db, session_id)
        if creds is None:
            subtask.status = "approved"  # type: ignore[assignment]
            subtask.updated_at = dt.now(UTC)  # type: ignore[assignment]
            await db.commit()
            await _maybe_complete_bootstrap(db, session_id, background_tasks)
            return ApproveSubtaskResponse(
                subtask_id=subtask.id,
                message="승인됨 (Linear 미연결 — 설정에서 Linear API 키를 등록하면 자동으로 이슈가 생성됩니다)",
            )

        # Linear 이슈 자동 생성
        from app.schemas.review_pipeline import LinearSyncHintSubtask  # noqa: PLC0415
        from app.services.linear_service import create_issues, get_initial_state_id  # noqa: PLC0415

        # 세션 설명을 이슈 본문 컨텍스트로 사용
        sess_for_desc_result = await db.execute(
            sa_select(OrchestratorSession).where(OrchestratorSession.id == session_id)
        )
        sess_for_desc = sess_for_desc_result.scalar_one_or_none()
        session_description = str(sess_for_desc.description) if sess_for_desc and sess_for_desc.description else None

        backlog_state_id = get_initial_state_id(creds.api_key, creds.team_id)
        hint = LinearSyncHintSubtask(
            title=str(subtask.title),
            role=str(subtask.assigned_role),
            draft_summary=str(subtask.description or subtask.title),
        )
        try:
            created = create_issues(
                creds.api_key,
                creds.team_id,
                [hint],
                state_id=backlog_state_id,
                session_description=session_description,
            )
        except Exception as exc:
            logger.warning("Linear 이슈 자동 생성 실패 subtask=%s: %s", subtask_id, exc)
            created = []

        if created:
            info = created[0]
            subtask.linear_issue_id = info.get("id") or None  # type: ignore[assignment]
            subtask.linear_identifier = info.get("identifier") or None  # type: ignore[assignment]
            subtask.linear_state = "Backlog"  # type: ignore[assignment]

        subtask.status = "approved"  # type: ignore[assignment]
        subtask.updated_at = dt.now(UTC)  # type: ignore[assignment]
        await db.commit()
        await _maybe_complete_bootstrap(db, session_id, background_tasks)

        if not subtask.linear_issue_id:
            return ApproveSubtaskResponse(
                subtask_id=subtask.id,
                message="승인됨 (Linear 이슈 생성 실패 — API 키 권한을 확인하세요)",
            )
        return ApproveSubtaskResponse(
            subtask_id=subtask.id,
            linear_identifier=str(subtask.linear_identifier or ""),
            transitioned_to="Backlog",
        )

    # 자격증명 조회 (헬퍼 사용)
    resolved = await _resolve_linear_credentials(db, session_id)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Linear 자격증명이 설정되지 않았습니다. 설정 → Linear에서 API 키와 Team ID를 입력하세요.",
        )
    api_key = resolved.api_key
    team_id = resolved.team_id

    # Todo 상태 ID 조회 → 이슈 상태 전이
    queued_state_id = get_queued_state_id(api_key, team_id)
    if not queued_state_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Linear 팀에 Todo 상태가 없습니다.",
        )

    ok = update_issue_state_id(api_key, str(subtask.linear_issue_id), queued_state_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Linear 이슈 상태 변경에 실패했습니다. API 키 권한을 확인하세요.",
        )

    # DB 상태 갱신
    subtask.linear_state = "Todo"
    subtask.updated_at = dt.now(UTC)
    await db.commit()

    return ApproveSubtaskResponse(
        subtask_id=subtask_id,
        linear_identifier=str(subtask.linear_identifier or ""),
        transitioned_to="Todo",
    )


# In Progress 이후 상태 — 되돌리기 불가
_LOCKED_STATES = {"In Progress", "Done", "In Review", "Cancelled"}
# 되돌리기 가능한 상태 (Todo, Backlog → Backlog)
_RESETTABLE_STATES = {"Todo", "Backlog"}


@router.post(
    "/sessions/{session_id}/subtasks/{subtask_id}/reset-to-wait",
    response_model=ResetToWaitResponse,
    status_code=status.HTTP_200_OK,
)
async def reset_subtask_to_wait(
    session_id: UUID,
    subtask_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResetToWaitResponse:
    """subtask의 Linear 이슈를 Todo/Backlog → Backlog로 되돌린다.

    In Progress 이후(In Progress, Done, In Review, Cancelled) 상태는 변경 불가.
    """
    from datetime import UTC
    from datetime import datetime as dt

    from sqlalchemy import select as sa_select

    from app.models.orchestrator import SubTask
    from app.services.linear_service import get_initial_state_id, update_issue_state_id

    st_result = await db.execute(
        sa_select(SubTask).where(
            SubTask.id == subtask_id,
            SubTask.session_id == session_id,
        )
    )
    subtask = st_result.scalar_one_or_none()
    if subtask is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="서브태스크를 찾을 수 없습니다",
        )

    if not subtask.linear_issue_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Linear 이슈가 아직 생성되지 않았습니다.",
        )

    current_state = subtask.linear_state or ""

    if current_state in _LOCKED_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"'{current_state}' 상태는 되돌릴 수 없습니다. "
                "In Progress 이후 항목은 변경이 금지됩니다."
            ),
        )

    if current_state not in _RESETTABLE_STATES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"'{current_state}' 상태는 Backlog 복귀 대상이 아닙니다.",
        )

    resolved = await _resolve_linear_credentials(db, session_id)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Linear 자격증명이 설정되지 않았습니다.",
        )
    api_key = resolved.api_key
    team_id = resolved.team_id

    wait_state_id = get_initial_state_id(api_key, team_id)
    if not wait_state_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Linear 팀에 Backlog 상태가 없습니다.",
        )

    ok = update_issue_state_id(api_key, str(subtask.linear_issue_id), wait_state_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Linear 이슈 상태 변경에 실패했습니다. API 키 권한을 확인하세요.",
        )

    previous_state = current_state
    subtask.linear_state = "Backlog"
    subtask.updated_at = dt.now(UTC)
    await db.commit()

    return ResetToWaitResponse(
        subtask_id=subtask_id,
        linear_identifier=str(subtask.linear_identifier or ""),
        previous_state=previous_state,
        transitioned_to="Backlog",
    )


@router.post(
    "/sessions/{session_id}/sync-linear-states",
    response_model=SyncLinearStatesResponse,
    status_code=status.HTTP_200_OK,
)
async def sync_linear_states(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SyncLinearStatesResponse:
    """세션의 모든 subtask Linear 상태를 실제 Linear 값으로 동기화한다.

    AI Team 진입 시 또는 수동 갱신 시 호출. Linear에서 직접 변경한 상태도 반영된다.
    In Progress 이후 상태(Done, In Review 등)도 DB에 정확히 업데이트한다.
    """
    from datetime import UTC
    from datetime import datetime as dt

    from sqlalchemy import select as sa_select

    from app.core.crypto import decrypt
    from app.models.orchestrator import OrchestratorSession, SubTask
    from app.models.project_linear_credentials import ProjectLinearCredentials
    from app.models.user_linear_credentials import UserLinearCredentials
    from app.services.linear_service import fetch_issue_states

    # linear_issue_id(UUID)가 있는 subtask만 조회 — UUID로 Linear API 조회
    st_result = await db.execute(
        sa_select(SubTask).where(
            SubTask.session_id == session_id,
            SubTask.linear_issue_id.is_not(None),
        )
    )
    subtasks = st_result.scalars().all()
    if not subtasks:
        return SyncLinearStatesResponse(synced_count=0, changed=[])

    # 세션 → 자격증명 조회
    sess_result = await db.execute(
        sa_select(OrchestratorSession).where(OrchestratorSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다")

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
        # 프로젝트 자격증명 없을 시 세션 생성자의 사용자 자격증명으로 폴백
        user_creds_result = await db.execute(
            sa_select(UserLinearCredentials).where(
                UserLinearCredentials.user_id == session.created_by
            )
        )
        user_creds = user_creds_result.scalar_one_or_none()
        if user_creds is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Linear 자격증명이 설정되지 않았습니다. 설정 → Linear에서 API 키와 Team ID를 입력하세요.",
            )
        api_key = decrypt(str(user_creds.encrypted_api_key))
        team_id = str(user_creds.team_id)

    # Linear에서 현재 상태 일괄 조회 (UUID → {identifier: state} 맵)
    issue_ids = [str(st.linear_issue_id) for st in subtasks]
    state_map = fetch_issue_states(api_key, team_id, issue_ids)

    now = dt.now(UTC)
    changed: list[SyncedSubtask] = []

    for subtask in subtasks:
        identifier = str(subtask.linear_identifier)
        new_state = state_map.get(identifier)
        if new_state is None:
            continue
        if subtask.linear_state != new_state:
            changed.append(SyncedSubtask(
                subtask_id=subtask.id,
                linear_identifier=identifier,
                previous_state=subtask.linear_state,
                current_state=new_state,
            ))
            subtask.linear_state = new_state
            subtask.updated_at = now

    if changed:
        await db.commit()

    return SyncLinearStatesResponse(
        synced_count=len(subtasks),
        changed=changed,
    )


@router.get(
    "/sessions/{session_id}/linear-team-states",
    response_model=LinearTeamStatesResponse,
    status_code=status.HTTP_200_OK,
)
async def get_linear_team_states(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinearTeamStatesResponse:
    """세션에 연결된 Linear 팀의 전체 워크플로우 상태 목록을 반환한다.

    프론트엔드가 상태 배지 렌더링 시 Linear 실제 상태명과 type을 사용하기 위해 호출.
    자격증명 미설정 시 빈 목록 반환 (UI 폴백 허용).
    """
    from sqlalchemy import select as sa_select

    from app.core.crypto import decrypt
    from app.models.orchestrator import OrchestratorSession
    from app.models.project_linear_credentials import ProjectLinearCredentials
    from app.models.user_linear_credentials import UserLinearCredentials
    from app.services.linear_service import get_team_states

    sess_result = await db.execute(
        sa_select(OrchestratorSession).where(OrchestratorSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="세션을 찾을 수 없습니다")

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
        user_creds_result = await db.execute(
            sa_select(UserLinearCredentials).where(
                UserLinearCredentials.user_id == session.created_by
            )
        )
        user_creds = user_creds_result.scalar_one_or_none()
        if user_creds is None:
            return LinearTeamStatesResponse(states=[])
        api_key = decrypt(str(user_creds.encrypted_api_key))
        team_id = str(user_creds.team_id)

    raw = get_team_states(api_key, team_id)
    raw.sort(key=lambda n: n.get("position", 0))
    states = [
        LinearTeamState(name=n["name"], type=n["type"], color=n["color"])
        for n in raw
    ]
    return LinearTeamStatesResponse(states=states)
