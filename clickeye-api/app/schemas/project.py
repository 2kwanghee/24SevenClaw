from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    project_type: str | None = Field(None, max_length=30)


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(None, pattern=r"^(active|archived)$")
    project_type: str | None = Field(None, max_length=30)


class ProjectResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    slug: str
    description: str | None
    status: str
    settings: dict  # type: ignore[type-arg]
    wizard_data: dict[str, Any] | None = None
    prototype_session_id: UUID | None = None
    pm_profile_id: UUID | None = None
    project_type: str | None = None
    bootstrap_status: str = "skipped"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
