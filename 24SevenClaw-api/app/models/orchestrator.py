import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base


class OrchestratorSession(Base):
    __tablename__ = "orchestrator_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    phase = Column(String(20), nullable=False, default="requested")
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    prompt_template = Column(Text, nullable=True)
    risk_flags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class SubTask(Base):
    __tablename__ = "subtasks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(
        Uuid,
        ForeignKey("orchestrator_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    assigned_role = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    order_index = Column(Integer, nullable=False, default=0)
    depends_on = Column(JSON, nullable=False, default=list)
    artifact_id = Column(
        Uuid, ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True
    )
    result_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PhaseEvent(Base):
    __tablename__ = "phase_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(
        Uuid,
        ForeignKey("orchestrator_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_phase = Column(String(20), nullable=True)
    new_phase = Column(String(20), nullable=False)
    actor_type = Column(String(20), nullable=False)  # "user", "agent", "system"
    actor_id = Column(Uuid, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
