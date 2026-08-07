"""관측 화면(관측 C) 집계 API (CE-388) — 전부 GET, 읽기 전용.

데이터는 전부 기존 테이블에 이미 적재되어 있다. `runs`/`seats` 는 각각
`PipelineRunService`/`SeatQuotaService` 를 그대로 재사용/래핑한다(중복 구현 금지).
관리자 가드는 형제 라우터(`llm_ledger.py`)와 동일하게 `require_permission("settings:manage")`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.observability import (
    DeliveryBoardResponse,
    DeliveryBoardTicketDetailResponse,
    ObservabilitySummaryResponse,
    ProjectSummaryResponse,
    SeatObservabilityResponse,
    UsagePivotResponse,
)
from app.schemas.pipeline_run import PipelineRunListResponse
from app.services.observability_service import ObservabilityService
from app.services.pipeline_run_service import PipelineRunService
from app.services.seat_quota_service import SeatQuotaService

router = APIRouter(
    prefix="/observability",
    tags=["observability"],
    dependencies=[Depends(require_permission("settings:manage"))],
)


@router.get("/summary", response_model=ObservabilitySummaryResponse)
async def get_summary(
    days: int = Query(default=7, ge=1, le=90),
    trend_days: int = Query(default=3, ge=1, le=14),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ObservabilitySummaryResponse:
    """대시보드 위젯 — 프로젝트/인테이크 상태 카운트, 최근 파이프라인 성공률, 딜리버리 피드."""
    return await ObservabilityService(db).summary(days=days, trend_days=trend_days)


@router.get("/usage", response_model=UsagePivotResponse)
async def get_usage(
    group_by: Literal["project_id", "seat_id", "model", "request_kind"] = Query(default="model"),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    task_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsagePivotResponse:
    """사용량 피벗 — 기간 × 축 그룹핑, task_id/project_id 지정 시 프로젝트 상세 드릴다운."""
    return await ObservabilityService(db).usage(
        from_=from_, to=to, group_by=group_by, task_id=task_id, project_id=project_id
    )


@router.get("/projects/{project_id}/summary", response_model=ProjectSummaryResponse)
async def get_project_summary(
    project_id: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectSummaryResponse:
    """프로젝트 상세 — ledger 토큰/비용 총합 + seat 별 그룹 + 최초/최근 활동 시각."""
    return await ObservabilityService(db).project_summary(project_id)


@router.get("/runs", response_model=PipelineRunListResponse)
async def list_observability_runs(
    issue_key: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PipelineRunListResponse:
    """실행 이력 — run 단위(최신순), 기존 PipelineRunService 그대로 재사용."""
    items, total = await PipelineRunService(db).list_runs(
        issue_key=issue_key, project_id=project_id, limit=limit, offset=offset
    )
    return PipelineRunListResponse(items=items, total=total)


@router.get("/runs/{issue_key}", response_model=PipelineRunListResponse)
async def get_observability_run_thread(
    issue_key: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PipelineRunListResponse:
    """issue_key 스레드 뷰 — 해당 티켓의 run 들만."""
    items, total = await PipelineRunService(db).list_runs(
        issue_key=issue_key, limit=limit, offset=offset
    )
    return PipelineRunListResponse(items=items, total=total)


@router.get("/delivery-board", response_model=DeliveryBoardResponse)
async def get_delivery_board(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryBoardResponse:
    """딜리버리 진행 보드 — 프로젝트별 티켓×단계 타임라인 집계(CE-411, 웹 E2 소비용)."""
    return await ObservabilityService(db).delivery_board()


@router.get(
    "/delivery-board/tickets/{issue_id}",
    response_model=DeliveryBoardTicketDetailResponse,
)
async def get_delivery_board_ticket_detail(
    issue_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryBoardTicketDetailResponse:
    """티켓 카드 클릭 시 Linear 원본 상세(상태·담당·라벨·본문·코멘트)를 lazy 조회.

    자격증명 부재/호출 실패는 502 대신 200 + available:false 로 반환한다.
    """
    # Column[UUID] 추론 대응 — 런타임 값은 UUID (mypy strict, CI 실측 오류 수정)
    return await ObservabilityService(db).delivery_board_ticket_detail(
        issue_id, cast(UUID, user.id)
    )


@router.get("/seats", response_model=SeatObservabilityResponse)
async def get_seats(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SeatObservabilityResponse:
    """시트 잔량 — 계정별 최신 스냅샷 + 시트 상태 + 최근 24h 소비."""
    return await SeatQuotaService(db).screen_view()
