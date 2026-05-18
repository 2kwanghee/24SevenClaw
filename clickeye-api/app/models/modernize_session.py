"""Modernize 위저드 세션 — 기존 코드 현대화 흐름의 영속 상태.

`prototype_session` 의 형제 모델. 사용자가 GitHub repo 를 선택해서 분석을 시작하면
한 행이 생성되고, 백그라운드 7-step 분석 pipeline 의 진행률 / 상태 / 에러를 저장한다.

원본 코드는 분석 후 즉시 삭제 (시크릿/소스 비보관 원칙). 메타 + LLM 요약만 영속.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    text,
)

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ModernizeSession(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "modernize_sessions"

    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        Uuid,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    installation_id = Column(
        Uuid,
        ForeignKey("github_installations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    repo_full_name = Column(String(300), nullable=False)
    repo_branch = Column(String(200), nullable=False, default="main", server_default=text("'main'"))
    commit_sha = Column(String(64), nullable=True)
    # 'versionup' | 'refactor' | 'language_migrate'
    scenario = Column(String(30), nullable=False)
    goals_text = Column(Text, nullable=True)
    target_stack = Column(JSON, nullable=True)
    # 'pending' | 'cloning' | 'analyzing' | 'recommending' | 'ready' | 'finalized' | 'failed'
    status = Column(
        String(30),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    progress_pct = Column(Integer, nullable=False, default=0, server_default=text("0"))
    error = Column(JSON, nullable=True)
    extra = Column(JSON, nullable=False, default=dict, server_default=text("'{}'::json"))
