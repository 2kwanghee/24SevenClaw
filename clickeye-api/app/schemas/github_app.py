"""GitHub App endpoint 의 Pydantic 스키마."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class InstallUrlResponse(BaseModel):
    """GitHub App 설치 URL + CSRF state JWT."""

    install_url: str
    state: str


class InstallationResponse(BaseModel):
    """GitHub Installation 정보 (callback 응답 + 조회 응답)."""

    id: UUID
    installation_id: int
    account_login: str
    account_type: str
    repository_selection: str
    installed_at: datetime
    revoked_at: datetime | None = None
    suspended_at: datetime | None = None

    model_config = {"from_attributes": True}


class CallbackQuery(BaseModel):
    """GitHub 가 callback URL 에 붙여 보내는 query 파라미터."""

    installation_id: int
    setup_action: str | None = None
    state: str
    code: str | None = None


class WebhookInstallation(BaseModel):
    """webhook payload 의 installation 필드."""

    id: int
    account: dict[str, Any] = Field(default_factory=dict)
    repository_selection: str | None = None
    permissions: dict[str, Any] = Field(default_factory=dict)
    suspended_at: datetime | None = None


class WebhookEvent(BaseModel):
    """GitHub webhook 의 핵심 필드만 추출."""

    action: str
    installation: WebhookInstallation | None = None
    # 그 외 payload 는 처리하지 않음 (raw json 으로 router 에서 직접 처리)
