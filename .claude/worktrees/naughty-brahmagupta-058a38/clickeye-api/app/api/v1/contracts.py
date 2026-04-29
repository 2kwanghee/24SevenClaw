"""중앙 계약 관리 엔드포인트.

- GET/POST/PUT/DELETE /api/v1/contracts (admin+)
- GET/POST/PATCH /api/v1/projects/{id}/contract-overrides
- POST /api/v1/projects/{id}/contracts/sync
- GET /api/v1/contracts/audit
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.contract import (
    CentralContractCreate,
    CentralContractListResponse,
    CentralContractResponse,
    CentralContractUpdate,
    ContractAuditLogListResponse,
    ContractAuditLogResponse,
    ContractSyncResponse,
    CustomerContractOverrideCreate,
    CustomerContractOverrideListResponse,
    CustomerContractOverrideResponse,
    CustomerContractOverrideUpdate,
)
from app.services.contract_service import ContractService

router = APIRouter(prefix="/contracts", tags=["contracts"])

# ── CentralContract CRUD (admin+) ────────────────────────────


@router.post(
    "/",
    response_model=CentralContractResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_contract(
    data: CentralContractCreate,
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> CentralContractResponse:
    service = ContractService(db)
    contract = await service.create_contract(data, actor_id=user.id)  # type: ignore[arg-type]
    return CentralContractResponse.model_validate(contract)


@router.get("/", response_model=CentralContractListResponse)
async def list_contracts(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    contract_type: str | None = Query(None, max_length=50),
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> CentralContractListResponse:
    service = ContractService(db)
    contracts, total = await service.list_contracts(
        offset=offset, limit=limit, contract_type=contract_type
    )
    return CentralContractListResponse(
        items=[CentralContractResponse.model_validate(c) for c in contracts],
        total=total,
    )


@router.get("/audit", response_model=ContractAuditLogListResponse)
async def list_audit_logs(
    contract_id: UUID | None = Query(None),
    change_type: str | None = Query(None, max_length=50),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> ContractAuditLogListResponse:
    service = ContractService(db)
    logs, total = await service.list_audit_logs(
        contract_id=contract_id,
        change_type=change_type,
        offset=offset,
        limit=limit,
    )
    return ContractAuditLogListResponse(
        items=[ContractAuditLogResponse.model_validate(log) for log in logs],
        total=total,
    )


@router.get("/{contract_id}", response_model=CentralContractResponse)
async def get_contract(
    contract_id: UUID,
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> CentralContractResponse:
    service = ContractService(db)
    contract = await service.get_contract(contract_id)
    return CentralContractResponse.model_validate(contract)


@router.put("/{contract_id}", response_model=CentralContractResponse)
async def update_contract(
    contract_id: UUID,
    data: CentralContractUpdate,
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> CentralContractResponse:
    service = ContractService(db)
    contract = await service.update_contract(
        contract_id, data, actor_id=user.id  # type: ignore[arg-type]
    )
    return CentralContractResponse.model_validate(contract)


@router.delete(
    "/{contract_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_contract(
    contract_id: UUID,
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    service = ContractService(db)
    await service.delete_contract(contract_id, actor_id=user.id)  # type: ignore[arg-type]


# ── Project Contract Overrides ────────────────────────────────

# 별도 라우터: /projects/{project_id}/contract-overrides
project_contracts_router = APIRouter(
    prefix="/projects/{project_id}/contract-overrides",
    tags=["contract-overrides"],
)


@project_contracts_router.get(
    "/", response_model=CustomerContractOverrideListResponse
)
async def list_project_overrides(
    project_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> CustomerContractOverrideListResponse:
    service = ContractService(db)
    overrides, total = await service.get_project_overrides(
        project_id, offset=offset, limit=limit
    )
    return CustomerContractOverrideListResponse(
        items=[
            CustomerContractOverrideResponse.model_validate(o) for o in overrides
        ],
        total=total,
    )


@project_contracts_router.post(
    "/",
    response_model=CustomerContractOverrideResponse,
    status_code=status.HTTP_201_CREATED,
)
async def apply_contract_to_project(
    project_id: UUID,
    data: CustomerContractOverrideCreate,
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> CustomerContractOverrideResponse:
    service = ContractService(db)
    override = await service.apply_contract_to_project(
        project_id, data, actor_id=user.id  # type: ignore[arg-type]
    )
    return CustomerContractOverrideResponse.model_validate(override)


@project_contracts_router.patch(
    "/{override_id}", response_model=CustomerContractOverrideResponse
)
async def update_override(
    project_id: UUID,
    override_id: UUID,
    data: CustomerContractOverrideUpdate,
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> CustomerContractOverrideResponse:
    service = ContractService(db)
    override = await service.update_customer_override(
        project_id, override_id, data, actor_id=user.id  # type: ignore[arg-type]
    )
    return CustomerContractOverrideResponse.model_validate(override)


# ── Contract Sync ─────────────────────────────────────────────

sync_router = APIRouter(
    prefix="/projects/{project_id}/contracts",
    tags=["contract-sync"],
)


@sync_router.post("/sync", response_model=ContractSyncResponse)
async def sync_contracts(
    project_id: UUID,
    user: User = Depends(require_permission("contract:manage")),
    db: AsyncSession = Depends(get_db),
) -> ContractSyncResponse:
    service = ContractService(db)
    synced_count, agent_ids = await service.sync_contracts_to_agent(
        project_id, actor_id=user.id  # type: ignore[arg-type]
    )
    return ContractSyncResponse(synced_count=synced_count, agent_ids=agent_ids)
