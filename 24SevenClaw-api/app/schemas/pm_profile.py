from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- PMProfile ---


class PMProfileResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    specialty: str
    description: str | None
    avatar_url: str | None
    skills: list[str]
    experience_areas: list[str]
    personality_traits: dict[str, Any]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PMProfileListResponse(BaseModel):
    items: list[PMProfileResponse]
    total: int


# --- PMComposition ---


class PMCompositionCreate(BaseModel):
    pm_profile_id: UUID
    role: str = Field(..., min_length=1, max_length=100)
    assigned_agents: list[str] = Field(default_factory=list)
    assigned_skills: list[str] = Field(default_factory=list)


class PMCompositionResponse(BaseModel):
    id: UUID
    prototype_id: UUID
    pm_profile_id: UUID
    role: str
    assigned_agents: list[str]
    assigned_skills: list[str]
    match_score: int
    reasoning: str | None

    model_config = {"from_attributes": True}


class PMCompositionUpdate(BaseModel):
    role: str | None = Field(None, min_length=1, max_length=100)
    assigned_agents: list[str] | None = None
    assigned_skills: list[str] | None = None


# --- PMRecommend ---


class PMRecommendRequest(BaseModel):
    prototype_id: UUID


class PMRecommendResponse(BaseModel):
    pm_profile: PMProfileResponse
    match_score: int
    reasoning: str | None


class PMRecommendListResponse(BaseModel):
    items: list[PMRecommendResponse]


# --- PMMetric ---


class PMMetricResponse(BaseModel):
    id: UUID
    pm_profile_id: UUID
    total_projects: int
    success_rate: float
    avg_rating: float
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- PMRating ---


class PMRatingCreate(BaseModel):
    project_id: UUID
    score: int = Field(..., ge=1, le=5)
    comment: str | None = None


class PMRatingResponse(BaseModel):
    id: UUID
    pm_profile_id: UUID
    project_id: UUID
    user_id: UUID
    score: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
