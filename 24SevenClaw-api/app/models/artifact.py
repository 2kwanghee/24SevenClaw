import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid

from app.database import Base


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    artifact_type = Column(String(50), nullable=False)  # "code", "document", "config" 등
    status = Column(String(20), nullable=False, default="draft")
    created_by_ai = Column(String(100), nullable=True)
    reviewed_by_ai = Column(String(100), nullable=True)
    revision_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ArtifactEvent(Base):
    __tablename__ = "artifact_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    artifact_id = Column(
        Uuid, ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type = Column(String(50), nullable=False)  # "status_transition"
    old_status = Column(String(20), nullable=True)
    new_status = Column(String(20), nullable=True)
    actor_type = Column(String(20), nullable=False)  # "user", "agent", "system"
    actor_id = Column(Uuid, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
