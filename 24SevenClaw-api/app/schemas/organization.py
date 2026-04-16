from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=200)
    size: str | None = Field(None, max_length=50)
    industry: str | None = Field(None, max_length=100)
    tech_stack: list[str] | None = None
    main_product: str | None = Field(None, max_length=500)
    business_type: str | None = Field(None, max_length=100)
    company_description: str | None = None


class OrganizationUpdate(BaseModel):
    company_name: str | None = Field(None, min_length=1, max_length=200)
    size: str | None = Field(None, max_length=50)
    industry: str | None = Field(None, max_length=100)
    tech_stack: list[str] | None = None
    main_product: str | None = Field(None, max_length=500)
    business_type: str | None = Field(None, max_length=100)
    company_description: str | None = None


class OrganizationResponse(BaseModel):
    id: UUID
    company_name: str
    size: str | None
    industry: str | None
    tech_stack: list[str] | None
    main_product: str | None
    business_type: str | None
    company_description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
