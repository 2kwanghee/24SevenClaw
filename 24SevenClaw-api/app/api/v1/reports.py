from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.report import ProjectReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/project/{project_id}",
    response_model=ProjectReportResponse,
)
async def get_project_report(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectReportResponse:
    """프로젝트 리포트를 집계하여 반환한다."""
    service = ReportService(db)
    return await service.generate_project_report(
        project_id=project_id, owner_id=user.id  # type: ignore[arg-type]
    )
