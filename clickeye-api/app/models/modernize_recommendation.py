"""Modernize 권장안 — "이슈 1건 = 권장안 1건" 원자단위.

분석 pipeline step 7 에서 시나리오별 LLM 호출로 생성된다. finalize 시
선택된(selected=True) 권장안만 Linear 자식 이슈로 일괄 등록되고,
`prompt_md` 가 ZIP 의 `.ralph/tasks/<linear-identifier>.md` 로 들어간다.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ModernizeRecommendation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "modernize_recommendations"

    session_id = Column(
        Uuid,
        ForeignKey("modernize_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 권장안 순서 (LLM 응답 순). priority 별도로 사용자 편집 가능.
    idx = Column(Integer, nullable=False)
    # 'upgrade' | 'replace' | 'refactor' | 'migrate' | 'remove'
    category = Column(String(30), nullable=False)
    target_path = Column(String(500), nullable=True)
    # {"pkg":"django","version":"3.2.18"} 등 시나리오별 다른 구조
    before = Column(JSON, nullable=True)
    after = Column(JSON, nullable=True)
    title = Column(String(300), nullable=False)
    rationale_md = Column(Text, nullable=True)
    # 'S' | 'M' | 'L'
    effort = Column(String(2), nullable=False, default="M", server_default=text("'M'"))
    # 'low' | 'med' | 'high'
    risk = Column(String(10), nullable=False, default="med", server_default=text("'med'"))
    priority = Column(Integer, nullable=False, default=50, server_default=text("50"))
    # auto_dev_pipeline.sh 가 그대로 사용할 LLM 지시문 (.ralph/tasks/<id>.md 로 베이크)
    prompt_md = Column(Text, nullable=True)
    # finalize 후 채워짐
    linear_issue_id = Column(String(100), nullable=True)
    linear_identifier = Column(String(50), nullable=True)
    # 사용자 검수 — 기본 true, PATCH 로 false 처리 가능
    selected = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    __table_args__ = (
        Index(
            "ix_modernize_recommendations_session_idx",
            "session_id",
            "idx",
        ),
    )
