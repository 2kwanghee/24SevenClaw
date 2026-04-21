"""품질 검증 게이트 API 엔드포인트.

Step 07 품질 검증 자동화.
- 검증 실행 생성/조회
- 개별 검사 결과 제출
- 최종 평가 (통과/실패 판정 + 상태 자동 전이)
- 검증 리포트 조회
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.quality_gate import (
    QualityCheckResponse,
    QualityCheckSubmit,
    QualityGateEvaluateRequest,
    QualityGateEventResponse,
    QualityGateReportResponse,
    QualityGateRunCreate,
    QualityGateRunListResponse,
    QualityGateRunResponse,
)
from app.services.quality_gate import QualityGateService

router = APIRouter(prefix="/quality-gate", tags=["quality-gate"])


# === 검증 실행 생성 ===


@router.post(
    "/sessions/{session_id}/runs",
    response_model=QualityGateRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_run(
    session_id: UUID,
    data: QualityGateRunCreate,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> QualityGateRunResponse:
    """품질 검증 실행을 생성한다. validating 단계에서만 가능."""
    service = QualityGateService(db)
    run = await service.create_run(session_id=session_id, data=data)
    return QualityGateRunResponse.model_validate(run)


# === 검증 실행 조회 ===


@router.get(
    "/sessions/{session_id}/runs",
    response_model=QualityGateRunListResponse,
)
async def list_runs(
    session_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> QualityGateRunListResponse:
    """세션의 품질 검증 실행 목록을 조회한다."""
    service = QualityGateService(db)
    runs, total = await service.list_runs(
        session_id=session_id, offset=offset, limit=limit
    )
    return QualityGateRunListResponse(
        items=[QualityGateRunResponse.model_validate(r) for r in runs],
        total=total,
    )


@router.get(
    "/runs/{run_id}",
    response_model=QualityGateRunResponse,
)
async def get_run(
    run_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> QualityGateRunResponse:
    """품질 검증 실행 상세 조회."""
    service = QualityGateService(db)
    run = await service.get_run(run_id)
    return QualityGateRunResponse.model_validate(run)


# === 개별 검사 결과 제출 ===


@router.post(
    "/runs/{run_id}/checks",
    response_model=QualityCheckResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_check(
    run_id: UUID,
    data: QualityCheckSubmit,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> QualityCheckResponse:
    """QA 에이전트가 개별 메트릭 검사 결과를 제출한다."""
    service = QualityGateService(db)
    check = await service.submit_check(run_id=run_id, data=data)
    return QualityCheckResponse.model_validate(check)


# === 최종 평가 ===


@router.post(
    "/runs/{run_id}/evaluate",
    response_model=QualityGateRunResponse,
)
async def evaluate_run(
    run_id: UUID,
    data: QualityGateEvaluateRequest,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> QualityGateRunResponse:
    """모든 검사 결과를 종합하여 통과/실패를 판정한다."""
    service = QualityGateService(db)
    run = await service.evaluate(run_id=run_id, auto_transition=data.auto_transition)
    return QualityGateRunResponse.model_validate(run)


# === 리포트 조회 ===


@router.get(
    "/runs/{run_id}/report",
    response_model=QualityGateReportResponse,
)
async def get_report(
    run_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> QualityGateReportResponse:
    """검증 결과 리포트를 조회한다."""
    service = QualityGateService(db)
    run, checks = await service.get_report(run_id)
    summary = {c.category: c.score for c in checks}
    return QualityGateReportResponse(
        run=QualityGateRunResponse.model_validate(run),
        checks=[QualityCheckResponse.model_validate(c) for c in checks],
        summary=summary,
    )


# === 이벤트 이력 ===


@router.get(
    "/runs/{run_id}/events",
    response_model=list[QualityGateEventResponse],
)
async def get_events(
    run_id: UUID,
    user: User = Depends(get_current_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> list[QualityGateEventResponse]:
    """품질 검증 이벤트 이력을 조회한다."""
    service = QualityGateService(db)
    events = await service.get_events(run_id)
    return [QualityGateEventResponse.model_validate(e) for e in events]
