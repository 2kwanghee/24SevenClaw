"""24SevenClaw Agent ↔ Cloud 프로토콜 타입 (Python/Pydantic)
TypeScript protocol/ 디렉토리와 반드시 동기화 유지
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


# === 공통 ===

class Message(BaseModel):
    id: str
    type: str
    timestamp: datetime
    payload: dict[str, Any]
    signature: str


# === Agent → Cloud ===

class RegisterPayload(BaseModel):
    registration_token: str
    hostname: str
    os: str
    docker_version: str
    agent_version: str
    capabilities: list[str]


class HeartbeatPayload(BaseModel):
    status: Literal["idle", "busy", "error"]
    uptime_seconds: int | None = None
    hostname: str | None = None
    os: str | None = None
    agent_version: str | None = None
    system: dict[str, float] | None = None
    environments: list[dict[str, Any]] | None = None
    active_tasks: list[str] | None = None


class StatusPayload(BaseModel):
    event: str
    project_id: str
    task_id: str | None = None
    progress: float | None = None
    message: str | None = None
    detail: dict[str, Any] | None = None


class ResultPayload(BaseModel):
    task_id: str
    ticket_id: str | None = None
    status: Literal["completed", "failed", "partial"]
    summary: str
    changes: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None


# === Cloud → Agent ===

class SetupEnvPayload(BaseModel):
    project_id: str
    project_name: str
    environment: dict[str, Any]
    git: dict[str, Any] | None = None


class DeployTicketPayload(BaseModel):
    ticket_id: str
    project_id: str
    title: str
    description: str
    priority: Literal["low", "medium", "high", "critical"]
    acceptance_criteria: list[str] | None = None
    context: dict[str, Any] | None = None


class BuildPayload(BaseModel):
    project_id: str
    build_type: Literal["full", "incremental"]
    command: str
    env_vars: dict[str, str] | None = None
    stream_logs: bool = False


class StopPayload(BaseModel):
    project_id: str
    target: Literal["all", "build", "service"]
    force: bool = False


# === 에러 ===

class ErrorPayload(BaseModel):
    code: str
    message: str
    original_message_id: str | None = None
    recoverable: bool
    suggestion: str | None = None


# === 산출물 상태 ===

ArtifactStatus = Literal[
    "draft",
    "reviewed",
    "revised",
    "approved",
    "in_development",
    "validated",
    "released",
]

ARTIFACT_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["reviewed"],
    "reviewed": ["revised", "approved"],
    "revised": ["reviewed"],
    "approved": ["in_development"],
    "in_development": ["validated"],
    "validated": ["released", "in_development"],
    "released": [],
}


class ArtifactTransitionRequest(BaseModel):
    target_status: ArtifactStatus
    actor_type: Literal["user", "agent", "system"]
    actor_id: str | None = None
    message: str | None = None


class ArtifactMeta(BaseModel):
    created_by_ai: str | None = None
    reviewed_by_ai: str | None = None
    last_transition_at: datetime | None = None
    revision_count: int = 0


# === 오케스트레이터 (마스터 PM AI) ===

OrchestratorPhase = Literal[
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

ORCHESTRATOR_TRANSITIONS: dict[str, list[str]] = {
    "requested": ["decomposed"],
    "decomposed": ["assigned"],
    "assigned": ["drafting"],
    "drafting": ["reviewing"],
    "reviewing": ["integrating", "drafting"],
    "integrating": ["validating"],
    "validating": ["approved", "integrating"],
    "approved": ["transitioning"],
    "transitioning": ["completed"],
    "completed": [],
}

AgentRole = Literal[
    "architect",
    "frontend",
    "backend",
    "qa",
    "security",
    "devops",
    "reviewer",
]

SubTaskStatus = Literal[
    "pending",
    "in_progress",
    "completed",
    "failed",
    "blocked",
]


class SubTaskPayload(BaseModel):
    title: str
    description: str | None = None
    assigned_role: AgentRole
    order_index: int
    depends_on: list[str] | None = None
    artifact_id: str | None = None


class PhaseTransitionPayload(BaseModel):
    target_phase: OrchestratorPhase
    actor_type: Literal["user", "agent", "system"]
    actor_id: str | None = None
    message: str | None = None
