from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- PMProfile ---


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
    # 메트릭 (없을 경우 기본값)
    usage_count: int = 0
    completed_projects: int = 0
    avg_rating: float = 0.0
    total_ratings: int = 0
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
    success_rate: float
    avg_completion_days: float

    model_config = {"from_attributes": True}


# --- PMRating ---


class PMRatingCreate(BaseModel):
    session_id: UUID
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class PMRatingResponse(BaseModel):
    id: UUID
    pm_id: UUID
    user_id: UUID
    session_id: UUID
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PMRatingListResponse(BaseModel):
    items: list[PMRatingResponse]
    total: int
