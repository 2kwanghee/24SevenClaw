from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- PrototypeSession ---


class PrototypeSessionCreate(BaseModel):
    organization_id: UUID
    solution_prompt: str = Field(..., description="솔루션을 설명하는 자연어 프롬프트")


class PrototypeSessionResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    solution_prompt: str | None
    parsed_requirements: dict[str, Any] | None
    status: str
    selected_prototype_id: UUID | None
    selected_pm_id: UUID | None
    current_step: int
    created_at: datetime
    updated_at: datetime

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
    variant_index: int
    title: str
    description: str | None
    design_pattern: str | None
    menu_structure: dict[str, Any] | None
    ui_structure: dict[str, Any] | None
    color_palette: dict[str, Any] | None
    thumbnail_url: str | None
    figma_file_key: str | None
    figma_embed_url: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PrototypeSelectRequest(BaseModel):
    prototype_id: UUID


class PrototypeListResponse(BaseModel):
    items: list[PrototypeResponse]
    total: int


class PrototypeDetailResponse(BaseModel):
    """프로토타입 상세 응답 — 세션 요약 정보 포함."""

    id: UUID
    session_id: UUID
    variant_index: int
    title: str
    description: str | None
    design_pattern: str | None
    menu_structure: dict[str, Any] | None
    ui_structure: dict[str, Any] | None
    color_palette: dict[str, Any] | None
    thumbnail_url: str | None
    figma_file_key: str | None
    figma_embed_url: str | None
    status: str
    # 세션 요약
    solution_prompt: str | None
    session_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateStartResponse(BaseModel):
    """프로토타입 생성 시작 응답 (202 Accepted)."""

    message: str
    session_id: UUID
