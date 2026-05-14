from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

IndustryTag = Literal[
    "manufacturing",
    "finance",
    "retail",
    "healthcare",
    "it-saas",
    "public",
    "education",
    "media",
]

# --- PMProfile ---


class PMProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    avatar_url: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    domain: str | None = Field(None, max_length=100)
    specialties: list[str] = Field(default_factory=list)
    personality: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    bio_long: str | None = None
    years_experience: int | None = Field(None, ge=0, le=50)
    preferred_solution_types: list[str] = Field(default_factory=list)
    tech_stack_tags: list[str] = Field(default_factory=list)
    industry_tags: list[IndustryTag] = Field(default_factory=list)
    language: str = Field(default="ko", max_length=8)


class PMProfileUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    avatar_url: str | None = Field(None, max_length=500)
    title: str | None = Field(None, max_length=200)
    description: str | None = None
    domain: str | None = Field(None, max_length=100)
    specialties: list[str] | None = None
    personality: dict[str, Any] | None = None
    is_active: bool | None = None
    bio_long: str | None = None
    years_experience: int | None = Field(None, ge=0, le=50)
    preferred_solution_types: list[str] | None = None
    tech_stack_tags: list[str] | None = None
    industry_tags: list[IndustryTag] | None = None
    language: str | None = Field(None, max_length=8)
    markdown_body: str | None = None


class PMProfileResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    avatar_url: str | None
    title: str | None
    description: str | None
    domain: str | None
    specialties: list[str]
    personality: dict[str, Any]
    is_active: bool
    created_at: datetime
    bio_long: str | None = None
    years_experience: int | None = None
    preferred_solution_types: list[str] = Field(default_factory=list)
    tech_stack_tags: list[str] = Field(default_factory=list)
    industry_tags: list[IndustryTag] = Field(default_factory=list)
    language: str = "ko"
    updated_at: datetime | None = None
    markdown_body: str | None = None

    model_config = {"from_attributes": True}


class PMProfileWithMetrics(BaseModel):
    """PM 프로필 + 메트릭 통합 응답."""

    id: UUID
    name: str
    slug: str
    avatar_url: str | None
    title: str | None
    description: str | None
    domain: str | None
    specialties: list[str]
    personality: dict[str, Any]
    is_active: bool
    created_at: datetime
    bio_long: str | None = None
    years_experience: int | None = None
    preferred_solution_types: list[str] = Field(default_factory=list)
    tech_stack_tags: list[str] = Field(default_factory=list)
    industry_tags: list[IndustryTag] = Field(default_factory=list)
    language: str = "ko"
    updated_at: datetime | None = None
    markdown_body: str | None = None
    # 메트릭 (없을 경우 기본값)
    usage_count: int = 0
    completed_projects: int = 0
    avg_rating: float = 0.0
    total_ratings: int = 0
    like_count: int = 0
    dislike_count: int = 0
    success_rate: float = 0.0
    avg_completion_days: float = 0.0

    model_config = {"from_attributes": True}


class PMProfileListResponse(BaseModel):
    items: list[PMProfileResponse]
    total: int


# --- PMComposition ---


class PMCompositionCreate(BaseModel):
    component_type: str = Field(..., min_length=1, max_length=100)
    component_slug: str = Field(..., min_length=1, max_length=100)
    component_name: str = Field(..., min_length=1, max_length=200)
    config: dict[str, Any] = Field(default_factory=dict)
    display_order: int = Field(default=0, ge=0)
    is_required: bool = False


class PMCompositionResponse(BaseModel):
    id: UUID
    pm_id: UUID
    component_type: str
    component_slug: str
    component_name: str
    config: dict[str, Any]
    display_order: int
    is_required: bool

    model_config = {"from_attributes": True}


class PMCompositionUpdate(BaseModel):
    component_name: str | None = Field(None, min_length=1, max_length=200)
    config: dict[str, Any] | None = None
    display_order: int | None = Field(None, ge=0)
    is_required: bool | None = None


# --- PMComposition Grouped ---


class PMCompositionGroupedResponse(BaseModel):
    """PM 구성 컴포넌트를 타입별로 그룹화한 응답."""

    agents: list[PMCompositionResponse] = []
    skills: list[PMCompositionResponse] = []
    hooks: list[PMCompositionResponse] = []
    mcp_servers: list[PMCompositionResponse] = []
    plugins: list[PMCompositionResponse] = []


# --- PMRecommend ---


class PMRecommendRequest(BaseModel):
    prototype_id: UUID
    session_id: UUID | None = None


class PMRecommendResponse(BaseModel):
    pm_profile: PMProfileResponse
    match_score: int
    reasoning: str | None


class PMRecommendListResponse(BaseModel):
    items: list[PMRecommendResponse]


# --- PMMetrics ---


class PMMetricsResponse(BaseModel):
    id: UUID
    pm_id: UUID
    usage_count: int
    completed_projects: int
    avg_rating: float
    total_ratings: int
    like_count: int = 0
    dislike_count: int = 0
    success_rate: float
    avg_completion_days: float

    model_config = {"from_attributes": True}


# --- PMRating ---


class PMRatingCreate(BaseModel):
    session_id: UUID
    reaction: Literal["like", "dislike"] | None = None
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = None

    @model_validator(mode="after")
    def rating_or_reaction_required(self) -> "PMRatingCreate":
        if self.reaction is None and self.rating is None:
            raise ValueError("reaction 또는 rating 중 하나는 반드시 입력해야 합니다")
        if self.rating is None:
            self.rating = 5 if self.reaction == "like" else 2
        return self


class PMRatingResponse(BaseModel):
    id: UUID
    pm_id: UUID
    user_id: UUID
    session_id: UUID
    rating: int
    reaction: str | None
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PMRatingListResponse(BaseModel):
    items: list[PMRatingResponse]
    total: int


# --- PMRecommendationLog ---


class PMRecommendationLogResponse(BaseModel):
    id: UUID
    session_id: UUID
    created_at: datetime | None
    input_snapshot: dict[str, Any]
    claude_raw: dict[str, Any] | None
    final_ranking: list[dict[str, Any]]
    selected_pm_id: UUID | None
    latency_ms: int | None
    is_fallback: bool

    model_config = {"from_attributes": True}


class PMRecommendationLogListResponse(BaseModel):
    items: list[PMRecommendationLogResponse]
    total: int


# --- Markdown 양방향 편집 ---


class PMMarkdownUpsertRequest(BaseModel):
    """YAML frontmatter + 본문 Markdown으로 PM 프로필을 업데이트하는 요청."""

    markdown_body: str = Field(..., description="YAML frontmatter + 섹션 본문 Markdown 텍스트")
