import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid

from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    creator_id = Column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="open")
    priority = Column(String(20), nullable=False, default="medium")
    assignee_type = Column(String(20), nullable=True)  # "agent", "human"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class TicketEvent(Base):
    __tablename__ = "ticket_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_id = Column(
        Uuid, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type = Column(String(50), nullable=False)
    old_value = Column(String(100), nullable=True)
    new_value = Column(String(100), nullable=True)
    message = Column(Text, nullable=True)
    actor_type = Column(String(20), nullable=False)  # "user", "agent", "system"
    actor_id = Column(Uuid, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
