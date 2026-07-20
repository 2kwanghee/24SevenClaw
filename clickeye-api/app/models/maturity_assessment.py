import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Uuid

from app.database import Base


class MaturityAssessment(Base):
    __tablename__ = "maturity_assessments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    answers = Column(JSON, nullable=False, default=dict)
    score = Column(Integer, nullable=False, default=0)
    level = Column(String(20), nullable=False)  # starter | intermediate | advanced
    recommended_preset_id = Column(
        Uuid, ForeignKey("presets.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
