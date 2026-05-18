"""GitHub Installation 에 매핑된 repo 메타 캐시 (24h TTL).

repo 목록 조회 시 GitHub API rate limit 보호를 위해 캐시. Modernize 위저드의
repo-select step 에서 사용된다. 강제 refresh 가 필요하면 `?refresh=true` 로 갱신.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    Uuid,
    text,
)

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class GitHubRepo(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "github_repos"

    installation_id = Column(
        Uuid,
        ForeignKey("github_installations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # GitHub 측 repository id
    gh_repo_id = Column(BigInteger, nullable=False)
    full_name = Column(String(300), nullable=False)
    default_branch = Column(
        String(200), nullable=False, default="main", server_default=text("'main'")
    )
    private = Column(Boolean, nullable=False, default=True, server_default=text("true"))
    language_primary = Column(String(50), nullable=True)
    pushed_at = Column(DateTime(timezone=True), nullable=True)
    cached_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint(
            "installation_id",
            "gh_repo_id",
            name="uq_github_repos_installation_gh_repo",
        ),
    )
