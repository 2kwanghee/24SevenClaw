"""LLM 사용량 원장 조회 API (CE-299) — admin/superadmin 전용.

원장은 게이트웨이가 자동 기록한다. 이 라우터는 조회(목록/집계)만 제공한다.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.models.llm_usage_ledger import LlmProvider, LlmUsageStatus
from app.models.user import User
from app.schemas.llm_ledger import (
    LlmProjectUsageSummary,
    LlmUsageEntryResponse,
    LlmUsageListResponse,
)
from app.services.llm_ledger_service import LlmLedgerService

router = APIRouter(
    prefix="/llm-ledger",
    tags=["admin-llm-ledger"],
    dependencies=[Depends(require_permission("settings:manage"))],
)


@router.get("", response_model=LlmUsageListResponse)
async def list_usage(
    project_id: UUID | None = Query(default=None),
    provider: LlmProvider | None = Query(default=None),
    status: LlmUsageStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LlmUsageListResponse:
    """원장 목록 조회 (프로바이더/상태/프로젝트 필터)."""
    svc = LlmLedgerService(db)
    rows, total = await svc.list_entries(
        project_id=project_id,
        provider=provider,
        status=status,
        limit=limit,
        offset=offset,
    )
    return LlmUsageListResponse(
        items=[LlmUsageEntryResponse.model_validate(r) for r in rows],
        total=total,
    )


@router.get("/summary", response_model=LlmProjectUsageSummary)
async def project_summary(
    project_id: UUID | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LlmProjectUsageSummary:
    """프로젝트별 토큰/비용 집계 (key_source 구분)."""
    svc = LlmLedgerService(db)
    return await svc.summary_by_project(project_id)
