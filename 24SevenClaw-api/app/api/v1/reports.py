from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.report import (
    PlatformSummaryResponse,
    ProjectKPIResponse,
    ProjectReportResponse,
)
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/project/{project_id}",
    response_model=ProjectReportResponse,
)
async def get_project_report(
    project_id: UUID,
    user: User = Depends(require_permission("report:view")),
    db: AsyncSession = Depends(get_db),
) -> ProjectReportResponse:
    """프로젝트 리포트를 집계하여 반환한다."""
    service = ReportService(db)
    return await service.generate_project_report(
        project_id=project_id, owner_id=user.id  # type: ignore[arg-type]
    )


@router.get(
    "/projects/{project_id}/kpi",
    response_model=ProjectKPIResponse,
)
async def get_project_kpi(
    project_id: UUID,
    user: User = Depends(require_permission("report:view")),
    db: AsyncSession = Depends(get_db),
) -> ProjectKPIResponse:
    """프로젝트 KPI 메트릭을 집계하여 반환한다."""
    service = ReportService(db)
    return await service.generate_project_kpi(
        project_id=project_id, owner_id=user.id  # type: ignore[arg-type]
    )


@router.get(
    "/platform/summary",
    response_model=PlatformSummaryResponse,
)
async def get_platform_summary(
    user: User = Depends(require_permission("platform:view")),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> PlatformSummaryResponse:
    """플랫폼 전체 KPI 요약 (superadmin 전용)."""
    service = ReportService(db)
    return await service.generate_platform_summary()
