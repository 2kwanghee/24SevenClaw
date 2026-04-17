from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- PrototypeSession ---


class PrototypeSessionCreate(BaseModel):
    organization_id: UUID
    solution_prompt: str = Field(..., description="솔루션을 설명하는 자연어 프롬프트")
    tech_stack: list[str] = Field(default_factory=list, description="사용자 선호 기술 스택")


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
    # 다양성 메타데이터 (ui_structure에서 추출)
    tech_stack_tags: list[str] = Field(default_factory=list)
    architecture_pattern: str | None = None
    variant_rationale: str | None = None
    is_recommended: bool = False
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
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
    tech_stack_tags: list[str] = Field(default_factory=list)
    architecture_pattern: str | None = None
    variant_rationale: str | None = None
    is_recommended: bool = False
    # 세션 요약
    solution_prompt: str | None
    session_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateStartResponse(BaseModel):
    """프로토타입 생성 시작 응답 (202 Accepted)."""

    task_id: UUID
    session_id: UUID
    status: str
    message: str


class PrototypeSessionUpdate(BaseModel):
    """PATCH /prototype-sessions/{id} 요청 스키마."""

    selected_prototype_id: UUID | None = None
    selected_pm_id: UUID | None = None
    current_step: int | None = Field(None, ge=1)


class PMRecommendItemResponse(BaseModel):
    """PM 추천 단일 항목."""

    pm_id: UUID
    name: str
    slug: str
    avatar_url: str | None
    title: str | None
    domain: str | None
    match_score: int
    reasoning: str


class RecommendPMsResponse(BaseModel):
    """POST /prototype-sessions/{id}/recommend-pms 응답."""

    items: list[PMRecommendItemResponse]


class FinalizeRequest(BaseModel):
    """POST /prototype-sessions/{id}/finalize 요청 스키마."""

    project_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class FinalizeResponse(BaseModel):
    """POST /prototype-sessions/{id}/finalize 응답."""

    project_id: UUID
    project_name: str
    session_id: UUID
    message: str
