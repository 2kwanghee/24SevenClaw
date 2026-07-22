import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid

from app.database import Base


class PMRating(Base):
    __tablename__ = "pm_ratings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    pm_id = Column(
        Uuid, ForeignKey("pm_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)  # 1~5
    reaction = Column(String(10), nullable=True)  # "like" | "dislike"
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
