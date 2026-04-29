import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, Uuid

from app.database import Base


class PMRecommendationLog(Base):
    __tablename__ = "pm_recommendation_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(Uuid, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    input_snapshot = Column(JSON, nullable=False, default=dict)
    claude_raw = Column(JSON, nullable=True)
    final_ranking = Column(JSON, nullable=False, default=list)
    selected_pm_id = Column(Uuid, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    is_fallback = Column(Boolean, nullable=False, default=False)
