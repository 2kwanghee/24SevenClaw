"""ClickEye Agent ↔ Cloud 프로토콜 타입 (Python/Pydantic)
TypeScript protocol/ 디렉토리와 반드시 동기화 유지
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, model_validator


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
    # CE-301: 러너 실행 팔·인증 모드 회계 (LLM 원장 구분 집계용)
    target: Literal["cloud", "desktop"] | None = None
    auth_mode: Literal["subscription_seat", "org_api_key"] | None = None
    changes: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None


class LogPayload(BaseModel):
    project_id: str
    task_id: str | None = None
    level: Literal["info", "warn", "error"]
    source: Literal["docker", "claude", "git", "build", "agent"]
    message: str
    truncated: bool | None = None


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


class RunPayload(BaseModel):
    project_id: str
    command: str
    port: int | None = None
    env_vars: dict[str, str] | None = None


class StopPayload(BaseModel):
    project_id: str
    target: Literal["all", "build", "service"]
    force: bool = False


# === 위치 무관 Runner 태스크 실행 (CE-301) ===
# TypeScript protocol/commands.ts 의 RunnerTaskPayload 와 반드시 동기화 유지.
# 데스크탑 러너(구독 시트, 주력)·클라우드 컨테이너(조직 키, 폴백)가 동일 소비하는 위치 무관 계약.
# TODO(P1/P3, 범위 밖): clickeye-agent DockerHandler 실행 핸들러 스키마를 본 계약에 정합화.

RunnerTarget = Literal["cloud", "desktop"]
RunnerAuthMode = Literal["subscription_seat", "org_api_key"]


class RunnerStreamingPolicy(BaseModel):
    logs: bool | None = None
    artifacts: bool | None = None


class RunnerTaskPayload(BaseModel):
    task_id: str
    project_id: str
    target: RunnerTarget
    auth_mode: RunnerAuthMode | None = None
    # 실행 명세 — ticket_id / prompt / command 중 최소 하나 필수(소비 핸들러가 검증, P1/P3).
    ticket_id: str | None = None
    prompt: str | None = None
    command: str | None = None
    model: str | None = None
    streaming: RunnerStreamingPolicy | None = None
    timeout_seconds: int | None = None

    @model_validator(mode="after")
    def _require_exec_spec(self):
        # W1: 실행 지시(ticket_id/prompt/command) 없는 no-op 태스크가 러너에 도달하는 것을 값싸게 방어.
        if not (self.ticket_id or self.prompt or self.command):
            raise ValueError("ticket_id/prompt/command 중 최소 하나 필수")
        return self


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


# === 프리셋 & 성숙도 ===

MaturityLevel = Literal["starter", "intermediate", "advanced"]


class PresetProfile(BaseModel):
    id: str
    name: str
    slug: str
    maturity_level: MaturityLevel
    solution_types: list[str]
    default_agents: list[str]
    default_skills: list[str]
    default_pipelines: list[str]
    description: str
    is_system: bool | None = None


class MaturityAssessmentRequest(BaseModel):
    answers: dict[str, int]


class MaturityQuestion(BaseModel):
    id: str
    text: str
    category: Literal["team", "process", "tooling", "ci", "ai"]
    weight: float
    options: list["MaturityOption"]


class MaturityOption(BaseModel):
    label: str
    score: int


class MaturityAssessmentResponse(BaseModel):
    level: MaturityLevel
    score: int
    recommended_preset_id: str | None = None
    reasoning: str


class NaturalLanguageConfigRequest(BaseModel):
    text: str
    project_id: str | None = None


class NaturalLanguageConfigResponse(BaseModel):
    suggested_agents: list[str]
    suggested_skills: list[str]
    suggested_pipelines: list[str]
    confidence: float
    reasoning: str


# === RBAC (역할 기반 접근 제어) ===

SystemRole = Literal["superadmin", "admin", "member", "viewer"]

OrgRole = Literal["org_admin", "org_member", "org_viewer"]

Permission = Literal[
    "project:create",
    "project:read",
    "project:update",
    "project:delete",
    "preset:manage",
    "contract:manage",
    "user:manage",
    "org:manage",
    "report:view",
    "rbac:manage",
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "superadmin": [
        "project:create", "project:read", "project:update", "project:delete",
        "preset:manage", "contract:manage", "user:manage", "org:manage",
        "report:view", "rbac:manage",
    ],
    "admin": [
        "project:create", "project:read", "project:update", "project:delete",
        "preset:manage", "contract:manage", "user:manage", "org:manage",
        "report:view",
    ],
    "member": [
        "project:create", "project:read", "project:update", "project:delete",
        "report:view",
    ],
    "viewer": [
        "project:read",
        "report:view",
    ],
}


class OrganizationMembershipPayload(BaseModel):
    id: str | None = None
    user_id: str
    organization_id: str
    org_role: OrgRole
    invited_by: str | None = None
    joined_at: str | None = None
    is_active: bool | None = None


class RoleAuditEntry(BaseModel):
    id: str | None = None
    actor_id: str
    target_user_id: str | None = None
    action: str
    old_value: str | None = None
    new_value: str
    resource: str | None = None
    created_at: str | None = None


# === 중앙 실행 계약 관리 ===

ContractSource = Literal["central", "custom"]

ContractType = Literal["settings", "skill", "agent", "pipeline"]

ContractChangeType = Literal["create", "update", "delete", "apply", "override", "sync"]


class CentralContractPayload(BaseModel):
    id: str | None = None
    slug: str
    contract_type: ContractType
    source: ContractSource
    version: str
    content: dict[str, Any]
    is_locked: bool = True
    allowed_overrides: list[str] = []
    created_at: str | None = None
    updated_at: str | None = None


class CustomerContractOverridePayload(BaseModel):
    id: str | None = None
    project_id: str
    central_contract_id: str
    override_content: dict[str, Any]
    approved_by: str | None = None
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class ContractAuditEntryPayload(BaseModel):
    id: str | None = None
    contract_id: str | None = None
    override_id: str | None = None
    actor_id: str
    change_type: ContractChangeType
    diff_snapshot: dict[str, Any] | None = None
    created_at: str | None = None


class ContractSyncItem(BaseModel):
    slug: str
    contract_type: ContractType
    version: str
    content: dict[str, Any]
    overrides: dict[str, Any]


class ContractSyncPayload(BaseModel):
    project_id: str
    contracts: list[ContractSyncItem]


# === Modernize 6단계 Phase 워크플로 ===
# 기존 ModernizeSession.status(pending→cloning→analyzing→recommending→ready→finalized)
# 파이프라인과 병행 도입되는 축 — 사용자에게 노출되는 위저드 단계를 표현한다.
# TypeScript protocol/modernize.ts 와 반드시 동기화 유지.

ModernizePhase = Literal[
    "asis",
    "requirements",
    "tobe",
    "plan",
    "preflight",
    "execute",
]

MODERNIZE_PHASE_ORDER: list[str] = [
    "asis",
    "requirements",
    "tobe",
    "plan",
    "preflight",
    "execute",
]


class StackDescriptor(BaseModel):
    db_type: str | None = None
    db_version: str | None = None
    runtime: str | None = None
    runtime_version: str | None = None
    framework: str | None = None
    framework_version: str | None = None
    infra: str | None = None
    extra: dict[str, Any] = {}


class RequirementsArtifactContent(BaseModel):
    as_is_stack: StackDescriptor
    to_be_stack: StackDescriptor
    notes_md: str | None = None


class ModernizePhaseArtifact(BaseModel):
    id: str
    session_id: str
    phase: ModernizePhase
    artifact_type: str
    content_md: str | None = None
    content_json: dict[str, Any] | None = None
    approved_at: str | None = None
    created_at: str
    updated_at: str
