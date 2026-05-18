"""GitHub App 설치 정보.

사용자가 ClickEye GitHub App 을 자신의 계정/조직에 설치하면 한 행이 생성된다.
installation token 자체는 보관하지 않는다 — 매 호출 시 GitHub App private key 로 JWT 발급 →
`/app/installations/{id}/access_tokens` 로 1h 유효 토큰을 얻는다.

Modernize 파이프라인 (MVP-2-A) 의 첫 단계인 repo-connect 에서 사용.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    Uuid,
    text,
)

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class GitHubInstallation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "github_installations"

    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        Uuid,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # GitHub 측 installation id (전역 unique)
    installation_id = Column(BigInteger, nullable=False, unique=True, index=True)
    # 설치 대상 계정 정보
    account_login = Column(String(200), nullable=False)
    account_type = Column(String(20), nullable=False)  # 'User' | 'Organization'
    target_type = Column(String(20), nullable=True)
    # App 부여 권한 (예: {"contents":"read","metadata":"read","pull_requests":"read"})
    permissions = Column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
    # 'all' (모든 repo) | 'selected' (선택된 repo 만)
    repository_selection = Column(
        String(20),
        nullable=False,
        default="selected",
        server_default=text("'selected'"),
    )
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    installed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    revoked_at = Column(DateTime(timezone=True), nullable=True)
