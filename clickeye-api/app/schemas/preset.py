from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

MaturityLevel = Literal["starter", "intermediate", "advanced"]


class PresetResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    maturity_level: str
    solution_types: list[str]
    default_agents: list[str]
    default_skills: list[str]
    default_pipelines: list[str]
    description: str | None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PresetListResponse(BaseModel):
    items: list[PresetResponse]
    total: int


class PresetApplyRequest(BaseModel):
    project_id: UUID


class PresetApplyResponse(BaseModel):
    project_id: UUID
    preset_id: UUID
    applied_agents: list[str]
    applied_skills: list[str]
    applied_pipelines: list[str]


class MaturityAssessmentRequest(BaseModel):
    answers: dict[str, int] = Field(..., min_length=1)
    organization_id: UUID | None = None


class MaturityOption(BaseModel):
    label: str
    score: int


class MaturityQuestion(BaseModel):
    id: str
    text: str
    category: Literal["team", "process", "tooling", "ci", "ai"]
    weight: float
    options: list[MaturityOption]


class MaturityAssessmentResponse(BaseModel):
    level: MaturityLevel
    score: int
    recommended_preset_id: UUID | None = None
    reasoning: str


class MaturityAssessmentDetailResponse(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID | None = None
    answers: dict[str, int]
    score: int
    level: MaturityLevel
    recommended_preset_id: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NaturalLanguageConfigRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)


class NaturalLanguageConfigResponse(BaseModel):
    suggested_agents: list[str]
    suggested_skills: list[str]
    suggested_pipelines: list[str]
    confidence: float
    reasoning: str
    # Claude analyze_solution() 풍부한 분석 필드 (위저드 prefill용)
    primary_tag: str | None = None
    tags: list[str] = Field(default_factory=list)
    tech_stack: dict[str, str | None] = Field(default_factory=dict)
    features: list[str] = Field(default_factory=list)
    complexity: str | None = None
    target_users: str | None = None
    key_requirements: list[str] = Field(default_factory=list)
