"""Modernize endpoint 의 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

# 위저드 6단계 Phase 축 — 기존 status 파이프라인과 병행 도입.
ModernizePhase = Literal[
    "asis",
    "requirements",
    "tobe",
    "plan",
    "preflight",
    "execute",
]


class InstallationListItem(BaseModel):
    """`/modernize/installations` 응답 항목."""

    id: UUID
    installation_id: int
    account_login: str
    account_type: str
    repository_selection: str
    installed_at: datetime
    suspended_at: datetime | None = None
    repo_count: int = 0

    model_config = {"from_attributes": True}


class RepoListItem(BaseModel):
    """`/modernize/installations/{id}/repos` 응답 항목."""

    gh_repo_id: int
    full_name: str
    default_branch: str
    private: bool
    language_primary: str | None = None
    pushed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ModernizeSession — 분석 세션
# ---------------------------------------------------------------------------


class ModernizeSessionCreate(BaseModel):
    """POST /modernize/sessions 요청 body."""

    installation_pk: UUID = Field(..., description="GitHubInstallation.id (UUID PK)")
    repo_full_name: str = Field(..., min_length=1, max_length=300)
    branch: str = Field(default="main", min_length=1, max_length=200)
    scenario: str = Field(..., description="'versionup' | 'refactor' | 'language_migrate'")
    goals_text: str | None = None
    target_stack: dict[str, Any] | None = None


class ModernizeSessionResponse(BaseModel):
    """세션 상태 + 진행률 응답. 폴링용."""

    id: UUID
    repo_full_name: str
    repo_branch: str
    commit_sha: str | None = None
    scenario: str
    status: str
    current_phase: ModernizePhase
    progress_pct: int
    error: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CodebaseAnalysisResponse(BaseModel):
    """`/modernize/sessions/{id}/analysis` 응답 — 분석 완료 후."""

    session_id: UUID
    loc_total: int | None = None
    file_count: int | None = None
    lang_distribution: dict[str, float] = Field(default_factory=dict)
    manifests: list[dict[str, Any]] = Field(default_factory=list)
    outdated_packages: list[dict[str, Any]] = Field(default_factory=list)
    framework_signals: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    llm_summary_md: str | None = None
    tokens_used: int | None = None
    analyzed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ModernizeRecommendation — 권장안 (M6)
# ---------------------------------------------------------------------------


class ModernizeRecommendationResponse(BaseModel):
    """권장안 응답 항목."""

    id: UUID
    idx: int
    category: str
    target_path: str | None = None
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    title: str
    rationale_md: str | None = None
    effort: str
    risk: str
    priority: int
    prompt_md: str | None = None
    linear_issue_id: str | None = None
    linear_identifier: str | None = None
    selected: bool
    depends_on: list[int] = Field(default_factory=list)
    wave: int = 0
    assigned_agent: str | None = None

    model_config = {"from_attributes": True}


class ModernizeRecommendationUpdate(BaseModel):
    """`PATCH /recommendations/{id}` 요청 body — 사용자 검수용."""

    selected: bool | None = None
    priority: int | None = Field(None, ge=1, le=100)
    prompt_md: str | None = None


# ---------------------------------------------------------------------------
# Finalize (M7)
# ---------------------------------------------------------------------------


class FinalizeRequest(BaseModel):
    """`POST /sessions/{id}/finalize` 요청 body."""

    create_linear_issues: bool = True
    project_id: UUID | None = Field(None, description="ProjectLinearCredentials 우선 사용 시")


class FinalizeResponse(BaseModel):
    """finalize 응답."""

    session_id: UUID
    status: str
    linear_parent_url: str | None = None
    linear_parent_identifier: str | None = None
    linear_child_count: int = 0
    linear_errors: list[str] = Field(default_factory=list)
    zip_url: str
    selected_recommendation_count: int = 0


# ---------------------------------------------------------------------------
# Phase 산출물 — requirements(As-Is/To-Be 스택) 등 단계별 검수 문서
# ---------------------------------------------------------------------------


class StackDescriptor(BaseModel):
    """단일 스택(As-Is 또는 To-Be) 서술자."""

    db_type: str | None = None
    db_version: str | None = None
    runtime: str | None = None
    runtime_version: str | None = None
    framework: str | None = None
    framework_version: str | None = None
    infra: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RequirementsArtifactContent(BaseModel):
    """requirements phase 산출물의 구조화 내용 — As-Is ↔ To-Be 스택 쌍."""

    as_is_stack: StackDescriptor
    to_be_stack: StackDescriptor
    notes_md: str | None = None


class ModernizePhaseArtifactResponse(BaseModel):
    """`modernize_phase_artifacts` 행 응답."""

    id: UUID
    session_id: UUID
    phase: ModernizePhase
    artifact_type: str
    content_md: str | None = None
    content_json: dict[str, Any] | None = None
    approved_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Plan phase (Phase 4) — 태스크 DAG + 웨이브/마일스톤
# ---------------------------------------------------------------------------


class PlanTaskItem(BaseModel):
    """`plan.json` 의 태스크 1건."""

    rec_id: str
    idx: int
    title: str
    category: str
    effort: str
    risk: str
    assigned_agent: str | None = None
    depends_on: list[int] = Field(default_factory=list)


class PlanWaveGroup(BaseModel):
    """`plan.json` 의 웨이브(마일스톤) 1건."""

    wave: int
    tasks: list[PlanTaskItem]


class ModernizePlanResponse(BaseModel):
    """`GET/POST /sessions/{id}/plan` 응답 — plan.json + modernization-plan.md."""

    session_id: UUID
    waves: list[PlanWaveGroup]
    plan_md: str
    approved_at: datetime | None = None
    generated_at: datetime | None = None
