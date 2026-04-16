from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- PrototypeSession ---


class PrototypeSessionCreate(BaseModel):
    organization_id: UUID
    user_input: dict[str, Any] = Field(
        ..., description="사용자 입력 (회사 정보 + 자연어 설명)"
    )


class PrototypeSessionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    user_input: dict[str, Any]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PrototypeSessionStatusResponse(BaseModel):
    id: UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Prototype ---


class PrototypeResponse(BaseModel):
    id: UUID
    session_id: UUID
    name: str
    solution_type: str
    config: dict[str, Any]
    reasoning: str | None
    is_selected: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PrototypeSelectRequest(BaseModel):
    prototype_id: UUID


class PrototypeListResponse(BaseModel):
    items: list[PrototypeResponse]
    total: int
