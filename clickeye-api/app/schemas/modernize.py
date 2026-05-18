"""Modernize endpoint 의 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
