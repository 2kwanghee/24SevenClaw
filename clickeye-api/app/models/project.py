import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text, Uuid, text

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    settings = Column(JSON, nullable=False, default=dict)
    wizard_data = Column(JSON, nullable=True)
    prototype_session_id = Column(
        Uuid,
        ForeignKey("prototype_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pm_profile_id = Column(
        Uuid,
        ForeignKey("pm_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_type = Column(
        String(30), nullable=True, default="legacy", server_default=text("'legacy'")
    )
    initial_task_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
