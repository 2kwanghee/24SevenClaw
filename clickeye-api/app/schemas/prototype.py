from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- PrototypeSession ---


class PrototypeSessionCreate(BaseModel):
    organization_id: UUID
    solution_prompt: str = Field(..., description="솔루션을 설명하는 자연어 프롬프트")
    tech_stack: list[str] = Field(default_factory=list, description="사용자 선호 기술 스택")
    industry: str | None = Field(
        None, description="업종 코드 (it, fintech, ecommerce, healthcare, ...)"
    )
    # 회사 컨텍스트 — Claude variant 생성 시 회사 특성에 맞는 추천 위해 전달
    company_size: str | None = Field(
        None, description="회사 규모 (startup/small/medium/mid-large/enterprise)"
    )
    business_type: str | None = Field(None, description="비즈니스 유형 (b2b/b2c/b2b2c/internal)")
    main_product: str | None = Field(None, description="주력 제품/서비스")
    company_description: str | None = Field(None, description="회사 설명 (자연어)")


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
    # 정량 지표 (Phase A — Claude 생성. 폴백 시 누락 허용)
    estimated_weeks_min: int | None = None
    estimated_weeks_max: int | None = None
    team_size_min: int | None = None
    team_size_max: int | None = None
    team_roles: list[str] = Field(default_factory=list)
    complexity_score: int | None = None
    scalability_score: int | None = None
    monthly_cost_min_usd: int | None = None
    monthly_cost_max_usd: int | None = None
    maintenance_difficulty: str | None = None
    skill_requirements: list[str] = Field(default_factory=list)
    match_reasoning: str | None = None
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
    # 정량 지표 (Phase A)
    estimated_weeks_min: int | None = None
    estimated_weeks_max: int | None = None
    team_size_min: int | None = None
    team_size_max: int | None = None
    team_roles: list[str] = Field(default_factory=list)
    complexity_score: int | None = None
    scalability_score: int | None = None
    monthly_cost_min_usd: int | None = None
    monthly_cost_max_usd: int | None = None
    maintenance_difficulty: str | None = None
    skill_requirements: list[str] = Field(default_factory=list)
    match_reasoning: str | None = None
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
    dimension_scores: dict[str, int] = Field(default_factory=dict)
    match_reasons: list[str] = Field(default_factory=list)


class RecommendPMsResponse(BaseModel):
    """POST /prototype-sessions/{id}/recommend-pms 응답."""

    items: list[PMRecommendItemResponse]


class RecommendComponentsResponse(BaseModel):
    """GET /prototype-sessions/{id}/recommend-components 응답."""

    agents: list[str] = Field(default_factory=list, description="추천 에이전트 ID 목록")
    skills: list[str] = Field(default_factory=list, description="추천 스킬 ID 목록")
    excluded_agents: list[str] = Field(default_factory=list, description="제외 에이전트 ID 목록")
    catalog_entry_slug: str | None = None
    reasoning: str | None = None


class FinalizeRequest(BaseModel):
    """POST /prototype-sessions/{id}/finalize 요청 스키마."""

    project_name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    linear_api_key: str | None = Field(None, description="Linear API 키 (선택)")
    linear_team_id: str | None = Field(None, description="Linear 팀 UUID (선택)")
    notion_api_key: str | None = Field(None, description="Notion API 키 (선택)")
    notion_database_id: str | None = Field(None, description="Notion 데이터베이스 UUID (선택)")
    hook_ids: list[str] = Field(default_factory=list, description="선택된 훅 ID 목록")


class FinalizeResponse(BaseModel):
    """POST /prototype-sessions/{id}/finalize 응답."""

    project_id: UUID
    project_name: str
    session_id: UUID
    message: str
    initial_task_url: str | None = None
