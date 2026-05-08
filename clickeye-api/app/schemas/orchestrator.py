from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

OrchestratorPhaseType = Literal[
    "requested",
    "decomposed",
    "assigned",
    "drafting",
    "reviewing",
    "integrating",
    "validating",
    "approved",
    "transitioning",
    "completed",
]

AgentRoleType = Literal[
    "architect",
    "frontend",
    "backend",
    "qa",
    "security",
    "devops",
    "reviewer",
]

SubTaskStatusType = Literal[
    "pending",
    "in_progress",
    "completed",
    "failed",
    "blocked",
]


# === 세션 ===


class SessionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None


class SessionResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: str | None
    phase: str
    created_by: UUID | None
    prompt_template: str | None
    risk_flags: list[str]
    analysis_result: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    items: list[SessionResponse]
    total: int


# === 서브태스크 ===


class SubTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    assigned_role: AgentRoleType
    order_index: int = Field(0, ge=0)
    depends_on: list[str] | None = None
    artifact_id: UUID | None = None


class SubTaskResponse(BaseModel):
    id: UUID
    session_id: UUID
    title: str
    description: str | None
    assigned_role: str
    status: str
    order_index: int
    depends_on: list[str]
    artifact_id: UUID | None
    result_summary: str | None
    linear_identifier: str | None = None
    linear_issue_id: str | None = None
    linear_state: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubTaskUpdate(BaseModel):
    status: SubTaskStatusType | None = None
    result_summary: str | None = Field(None, max_length=2000)
    artifact_id: UUID | None = None


# === 단계 전이 ===


class PhaseTransitionRequest(BaseModel):
    target_phase: OrchestratorPhaseType
    message: str | None = Field(None, max_length=500)


class PhaseEventResponse(BaseModel):
    id: UUID
    session_id: UUID
    old_phase: str | None
    new_phase: str
    actor_type: str
    actor_id: UUID | None
    message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# === 작업 분해 ===


class DecomposeRequest(BaseModel):
    hints: list[str] | None = None


class DecomposeResponse(BaseModel):
    session: SessionResponse
    subtasks: list[SubTaskResponse]
    key_source: Literal["user", "server"] = "server"


# === 팀 배정 ===


class AssignRequest(BaseModel):
    overrides: dict[str, AgentRoleType] | None = None


class AssignResponse(BaseModel):
    session: SessionResponse
    subtasks: list[SubTaskResponse]


# === 세션 요약 ===


class SessionSummary(BaseModel):
    session: SessionResponse
    subtasks: list[SubTaskResponse]
    phase_history: list[PhaseEventResponse]
