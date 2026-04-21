import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, Uuid

from app.database import Base


class ReviewRound(Base):
    """교차 리뷰 라운드 — 메인 AI 초안 + 서브 AI 리뷰 1회 사이클."""

    __tablename__ = "review_rounds"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(
        Uuid,
        ForeignKey("orchestrator_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subtask_id = Column(
        Uuid,
        ForeignKey("subtasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    round_number = Column(Integer, nullable=False, default=1)
    status = Column(String(30), nullable=False, default="draft_submitted")
    # 메인 AI (초안 작성)
    main_ai_role = Column(String(50), nullable=False)
    draft_content = Column(Text, nullable=False)
    # 서브 AI (교차 리뷰)
    sub_ai_role = Column(String(50), nullable=True)
    review_type = Column(String(30), nullable=True)  # cross_review, counter_argument, alternative
    review_content = Column(Text, nullable=True)
    review_score = Column(Integer, nullable=True)  # 0~100
    # diff + 병합
    diff_summary = Column(Text, nullable=True)
    merged_content = Column(Text, nullable=True)
    merge_strategy = Column(String(30), nullable=True)  # accept_draft, accept_review, manual_merge
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ReviewEvent(Base):
    """교차 리뷰 이벤트 이력."""

    __tablename__ = "review_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    round_id = Column(
        Uuid,
        ForeignKey("review_rounds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False)
    actor_type = Column(String(20), nullable=False)  # user, agent, system
    actor_id = Column(Uuid, nullable=True)
    message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
