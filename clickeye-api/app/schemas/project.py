from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    project_type: str | None = Field(None, max_length=30)
    organization_id: UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(None, pattern=r"^(active|archived)$")
    project_type: str | None = Field(None, max_length=30)


class ProjectResponse(BaseModel):
    id: UUID
    owner_id: UUID
    organization_id: UUID | None = None
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
    last_zip_downloaded_at: datetime | None = None
    last_env_downloaded_at: datetime | None = None
    anthropic_key_status: Literal["fresh", "stale", "no_saved_key", "never_downloaded", "n/a"] = (
        "no_saved_key"
    )
    linear_key_status: Literal["fresh", "stale", "no_saved_key", "never_downloaded"] = (
        "no_saved_key"
    )
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int


class ProjectResetResponse(BaseModel):
    project_id: UUID
    new_license_key: str | None = None
    deleted_counts: dict[str, int]
