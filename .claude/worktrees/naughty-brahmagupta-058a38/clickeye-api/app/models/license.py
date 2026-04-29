import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Uuid

from app.database import Base


class License(Base):
    __tablename__ = "licenses"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    license_key = Column(String(255), unique=True, nullable=False, index=True)
    plan = Column(String(50), nullable=False, default="basic")
    status = Column(String(20), nullable=False, default="active")
    max_agents = Column(Integer, nullable=False, default=1)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
