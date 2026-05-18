"""Modernize endpoint 의 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}


class ModernizeRecommendationUpdate(BaseModel):
    """`PATCH /recommendations/{id}` 요청 body — 사용자 검수용."""

    selected: bool | None = None
    priority: int | None = Field(None, ge=1, le=100)
    prompt_md: str | None = None
