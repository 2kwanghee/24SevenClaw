from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ArtifactStatusType = Literal[
    "draft",
    "reviewed",
    "revised",
    "approved",
    "in_development",
    "validated",
    "released",
]


class ArtifactCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    artifact_type: str = Field(..., min_length=1, max_length=50)
    created_by_ai: str | None = Field(None, max_length=100)


class ArtifactResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    artifact_type: str
    status: str
    created_by_ai: str | None
    reviewed_by_ai: str | None
    revision_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArtifactListResponse(BaseModel):
    items: list[ArtifactResponse]
    total: int


class ArtifactTransitionRequest(BaseModel):
    target_status: ArtifactStatusType
    actor_type: Literal["user", "agent", "system"]
    actor_id: UUID | None = None
    message: str | None = Field(None, max_length=500)


class ArtifactEventResponse(BaseModel):
    id: UUID
    artifact_id: UUID
    event_type: str
    old_status: str | None
    new_status: str | None
    actor_type: str
    actor_id: UUID | None
    message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ArtifactTransitionResponse(BaseModel):
    artifact: ArtifactResponse
    event: ArtifactEventResponse
