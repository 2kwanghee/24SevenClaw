from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.control_tower import (
    CustomerDetail,
    CustomerListResponse,
    CustomerStatusUpdate,
    CustomerSummary,
    ProjectListResponse,
    ProjectOverview,
    ProjectTransferRequest,
)
from app.services.control_tower_service import ControlTowerService

router = APIRouter(prefix="/control-tower", tags=["control-tower"])

_READ = Depends(require_permission("control_tower:read"))
_WRITE = Depends(require_permission("control_tower:write"))


@router.get("/customers", response_model=CustomerListResponse)
async def list_customers(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    status: str | None = Query(None),
    user: User = _READ,
    db: AsyncSession = Depends(get_db),
) -> CustomerListResponse:
    """고객사 목록 — 프로젝트 수·활성 세션 수 집계 포함."""
    service = ControlTowerService(db)
    items, total = await service.list_customers(
        offset=offset, limit=limit, search=search, status_filter=status
    )
    return CustomerListResponse(
        items=[CustomerSummary(**item) for item in items],
        total=total,
    )


@router.get("/customers/{org_id}", response_model=CustomerDetail)
async def get_customer(
    org_id: UUID,
    user: User = _READ,
    db: AsyncSession = Depends(get_db),
) -> CustomerDetail:
    """고객사 상세 정보."""
    service = ControlTowerService(db)
    data = await service.get_customer(org_id)
    return CustomerDetail(**data)


@router.get("/customers/{org_id}/projects", response_model=ProjectListResponse)
async def list_customer_projects(
    org_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = _READ,
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    """고객사의 프로젝트 목록."""
    service = ControlTowerService(db)
    items, total = await service.list_customer_projects(
        org_id=org_id, offset=offset, limit=limit
    )
    return ProjectListResponse(
        items=[ProjectOverview(**item) for item in items],
        total=total,
    )


@router.get("/projects/{project_id}/overview", response_model=ProjectOverview)
async def get_project_overview(
    project_id: UUID,
    user: User = _READ,
    db: AsyncSession = Depends(get_db),
) -> ProjectOverview:
    """프로젝트 종합 현황 (세션/활성 세션 카운터)."""
    service = ControlTowerService(db)
    data = await service.get_project_overview(project_id)
    return ProjectOverview(**data)


@router.post(
    "/customers/{org_id}/status",
    response_model=CustomerDetail,
    status_code=status.HTTP_200_OK,
)
async def set_customer_status(
    org_id: UUID,
    data: CustomerStatusUpdate,
    user: User = _WRITE,
    db: AsyncSession = Depends(get_db),
) -> CustomerDetail:
    """고객사 상태 변경 (active | paused | archived)."""
    service = ControlTowerService(db)
    result = await service.set_customer_status(org_id, data.status)
    return CustomerDetail(**result)


@router.post(
    "/projects/{project_id}/transfer",
    response_model=ProjectOverview,
    status_code=status.HTTP_200_OK,
)
async def transfer_project(
    project_id: UUID,
    data: ProjectTransferRequest,
    user: User = _WRITE,
    db: AsyncSession = Depends(get_db),
) -> ProjectOverview:
    """프로젝트를 다른 고객사로 이동."""
    service = ControlTowerService(db)
    result = await service.transfer_project(project_id, data.to_organization_id)
    return ProjectOverview(**result)
