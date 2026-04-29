"""중앙 계약 관리 스키마."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- CentralContract ---


class CentralContractCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=200)
    contract_type: str = Field(..., min_length=1, max_length=50)
    source: str = Field(..., min_length=1, max_length=200)
    version: str = Field("1.0.0", max_length=50)
    content: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None
    is_locked: bool = True
    allowed_overrides: list[str] = Field(default_factory=list)


class CentralContractUpdate(BaseModel):
    contract_type: str | None = Field(None, min_length=1, max_length=50)
    source: str | None = Field(None, min_length=1, max_length=200)
    version: str | None = Field(None, max_length=50)
    content: dict[str, Any] | None = None
    description: str | None = None
    is_locked: bool | None = None
    allowed_overrides: list[str] | None = None


class CentralContractResponse(BaseModel):
    id: UUID
    slug: str
    contract_type: str
    source: str
    version: str
    content: dict[str, Any]
    description: str | None
    is_locked: bool
    allowed_overrides: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CentralContractListResponse(BaseModel):
    items: list[CentralContractResponse]
    total: int


# --- CustomerContractOverride ---


class CustomerContractOverrideCreate(BaseModel):
    central_contract_id: UUID
    override_content: dict[str, Any] = Field(default_factory=dict)


class CustomerContractOverrideUpdate(BaseModel):
    override_content: dict[str, Any]


class CustomerContractOverrideResponse(BaseModel):
    id: UUID
    project_id: UUID
    central_contract_id: UUID
    override_content: dict[str, Any]
    approved_by: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CustomerContractOverrideListResponse(BaseModel):
    items: list[CustomerContractOverrideResponse]
    total: int


# --- ContractAuditLog ---


class ContractAuditLogResponse(BaseModel):
    id: UUID
    contract_id: UUID | None
    override_id: UUID | None
    actor_id: UUID
    change_type: str
    diff_snapshot: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ContractAuditLogListResponse(BaseModel):
    items: list[ContractAuditLogResponse]
    total: int


# --- Sync ---


class ContractSyncResponse(BaseModel):
    synced_count: int
    agent_ids: list[str]
