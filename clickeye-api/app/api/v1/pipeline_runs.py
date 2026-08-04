"""파이프라인 실행 이력 API (CE-363).

두 진입점:
- `POST /pipeline-runs/events` — 머신 인제스트(파이프라인發, X-Governance-Token 보호).
  항상 202 비블로킹 계약(호출측 파이프라인을 절대 죽이지 않는다).
- `GET /pipeline-runs` — 브라우저 조회(admin/superadmin, JWT).
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.governance import verify_governance_token
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.pipeline_run import (
    PipelineEventsIngestRequest,
    PipelineRunListResponse,
)
from app.services.pipeline_run_service import PipelineRunService

router = APIRouter(prefix="/pipeline-runs", tags=["pipeline-runs"])


@router.post(
    "/events",
    status_code=202,
    dependencies=[Depends(verify_governance_token)],
)
async def ingest_events(
    body: PipelineEventsIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """파이프라인 단계 이벤트 배치 인제스트 — X-Governance-Token 보호(JWT 아님).

    항상 202(비블로킹 계약):
    - 관측 계열 공통 스위치 FEATURE_LLM_USAGE_INGEST off → {status: disabled} (에러 아님).
    - 정상 → {status: accepted, count: N}. 멱등 upsert 는 PipelineRunService 위임.
    """
    if not settings.feature_llm_usage_ingest:
        return {"status": "disabled"}
    count = await PipelineRunService(db).ingest(body.events)
    return {"status": "accepted", "count": count}


@router.get(
    "",
    response_model=PipelineRunListResponse,
    dependencies=[Depends(require_permission("settings:manage"))],
)
async def list_runs(
    issue_key: str | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PipelineRunListResponse:
    """run 단위(최신순) 실행 이력 조회 — 이벤트 스레드 + 그 티켓의 소비 토큰."""
    svc = PipelineRunService(db)
    items, total = await svc.list_runs(
        issue_key=issue_key,
        project_id=project_id,
        limit=limit,
        offset=offset,
    )
    return PipelineRunListResponse(items=items, total=total)
