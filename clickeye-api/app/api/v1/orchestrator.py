from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.orchestrator import (
    AssignRequest,
    AssignResponse,
    DecomposeRequest,
    DecomposeResponse,
    PhaseEventResponse,
    PhaseTransitionRequest,
    SessionCreate,
    SessionListResponse,
    SessionResponse,
    SessionSummary,
    SubTaskCreate,
    SubTaskResponse,
    SubTaskUpdate,
)
from app.services.orchestrator_service import OrchestratorService

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


# === 세션 CRUD ===


@router.post(
    "/projects/{project_id}/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    project_id: UUID,
    data: SessionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """오케스트레이션 세션을 생성한다."""
    service = OrchestratorService(db)
    session = await service.create_session(
        project_id=project_id, user_id=user.id, data=data
    )
    return SessionResponse.model_validate(session)


@router.get(
    "/projects/{project_id}/sessions",
    response_model=SessionListResponse,
)
async def list_sessions(
    project_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    phase: str | None = Query(None),
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> SessionListResponse:
    """프로젝트의 오케스트레이션 세션 목록을 조회한다."""
    service = OrchestratorService(db)
    sessions, total = await service.list_sessions(
        project_id=project_id, offset=offset, limit=limit, phase_filter=phase
    )
    return SessionListResponse(
        items=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> None:
    """오케스트레이션 세션과 관련 데이터(서브태스크, 이력, 리뷰)를 삭제한다."""
    service = OrchestratorService(db)
    await service.delete_session(session_id)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """오케스트레이션 세션 상세 조회."""
    service = OrchestratorService(db)
    session = await service.get_session(session_id)
    return SessionResponse.model_validate(session)


@router.get("/sessions/{session_id}/summary", response_model=SessionSummary)
async def get_session_summary(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> SessionSummary:
    """세션 요약 보고서 (세션 + 서브태스크 + 단계 이력)."""
    service = OrchestratorService(db)
    session, subtasks, history = await service.get_summary(session_id)
    return SessionSummary(
        session=SessionResponse.model_validate(session),
        subtasks=[SubTaskResponse.model_validate(st) for st in subtasks],
        phase_history=[PhaseEventResponse.model_validate(e) for e in history],
    )


# === 작업 분해 & 팀 배정 ===


@router.post(
    "/sessions/{session_id}/decompose",
    response_model=DecomposeResponse,
)
async def decompose_session(
    session_id: UUID,
    data: DecomposeRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> DecomposeResponse:
    """세션의 작업을 분해하여 서브태스크를 자동 생성한다."""
    service = OrchestratorService(db)
    session, subtasks = await service.decompose(session_id=session_id, data=data)
    return DecomposeResponse(
        session=SessionResponse.model_validate(session),
        subtasks=[SubTaskResponse.model_validate(st) for st in subtasks],
    )


@router.post(
    "/sessions/{session_id}/assign",
    response_model=AssignResponse,
)
async def assign_team(
    session_id: UUID,
    data: AssignRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> AssignResponse:
    """서브태스크에 AI 팀을 배정한다."""
    service = OrchestratorService(db)
    session, subtasks = await service.assign(session_id=session_id, data=data)
    return AssignResponse(
        session=SessionResponse.model_validate(session),
        subtasks=[SubTaskResponse.model_validate(st) for st in subtasks],
    )


# === 단계 전이 ===


@router.put(
    "/sessions/{session_id}/transition",
    response_model=SessionResponse,
)
async def transition_session(
    session_id: UUID,
    data: PhaseTransitionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    """세션의 단계를 전이한다."""
    service = OrchestratorService(db)
    session, _event = await service.transition(
        session_id=session_id,
        data=data,
        actor_type="user",
        actor_id=user.id,
    )
    return SessionResponse.model_validate(session)


@router.get(
    "/sessions/{session_id}/history",
    response_model=list[PhaseEventResponse],
)
async def get_phase_history(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> list[PhaseEventResponse]:
    """세션의 단계 변경 이력을 조회한다."""
    service = OrchestratorService(db)
    events = await service.get_phase_history(session_id)
    return [PhaseEventResponse.model_validate(e) for e in events]


# === 리스크 탐지 ===


@router.get(
    "/sessions/{session_id}/risks",
    response_model=list[str],
)
async def detect_risks(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """세션의 리스크를 탐지하여 반환한다."""
    service = OrchestratorService(db)
    return await service.detect_risks(session_id)


# === 서브태스크 관리 ===


@router.post(
    "/sessions/{session_id}/subtasks",
    response_model=SubTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_subtask(
    session_id: UUID,
    data: SubTaskCreate,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> SubTaskResponse:
    """서브태스크를 수동으로 추가한다."""
    service = OrchestratorService(db)
    subtask = await service.create_subtask(session_id=session_id, data=data)
    return SubTaskResponse.model_validate(subtask)


@router.get(
    "/sessions/{session_id}/subtasks",
    response_model=list[SubTaskResponse],
)
async def list_subtasks(
    session_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> list[SubTaskResponse]:
    """세션의 서브태스크 목록을 조회한다."""
    service = OrchestratorService(db)
    subtasks = await service.get_subtasks(session_id)
    return [SubTaskResponse.model_validate(st) for st in subtasks]


@router.patch(
    "/subtasks/{subtask_id}",
    response_model=SubTaskResponse,
)
async def update_subtask(
    subtask_id: UUID,
    data: SubTaskUpdate,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> SubTaskResponse:
    """서브태스크 상태/결과를 업데이트한다."""
    service = OrchestratorService(db)
    subtask = await service.update_subtask(subtask_id=subtask_id, data=data)
    return SubTaskResponse.model_validate(subtask)
