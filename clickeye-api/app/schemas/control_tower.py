from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerSummary(BaseModel):
    id: UUID
    company_name: str
    org_type: str
    customer_status: str
    account_manager_id: UUID | None
    account_manager_name: str | None
    project_count: int
    active_session_count: int
    created_at: datetime | None

    model_config = {"from_attributes": True}


class CustomerListResponse(BaseModel):
    items: list[CustomerSummary]
    total: int


class CustomerDetail(BaseModel):
    id: UUID
    company_name: str
    org_type: str
    customer_status: str
    account_manager_id: UUID | None
    account_manager_name: str | None
    size: str | None
    industry: str | None
    main_product: str | None
    business_type: str | None
    company_description: str | None
    features: dict[str, Any]
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class OrgFeatureUpdateRequest(BaseModel):
    feature_name: str = Field(..., description="기능 플래그 이름 (예: live_preview_enabled)")
    value: bool = Field(..., description="활성화 여부")


class ProjectOverview(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    project_type: str | None
    owner_id: UUID
    owner_name: str | None
    organization_id: UUID | None
    session_count: int
    active_session_count: int
    created_at: datetime | None
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectOverview]
    total: int


class CustomerStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|paused|archived)$")


class ProjectTransferRequest(BaseModel):
    to_organization_id: UUID
