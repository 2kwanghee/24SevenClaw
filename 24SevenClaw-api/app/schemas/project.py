from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = Field(None, pattern=r"^(active|archived)$")


class ProjectResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    slug: str
    description: str | None
    status: str
    settings: dict  # type: ignore[type-arg]
    wizard_data: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
