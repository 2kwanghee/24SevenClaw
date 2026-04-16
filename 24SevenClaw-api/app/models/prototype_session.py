import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text, Uuid

from app.database import Base


class PrototypeSession(Base):
    __tablename__ = "prototype_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_input = Column(JSON, nullable=False, default=dict)
    status = Column(
        String(20), nullable=False, default="pending"
    )  # pending | generating | completed | failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Prototype(Base):
    __tablename__ = "prototypes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(
        Uuid,
        ForeignKey("prototype_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)
    solution_type = Column(
        String(50), nullable=False
    )  # saas | rest-api | fullstack | internal-tool | mvp | custom
    config = Column(JSON, nullable=False, default=dict)
    reasoning = Column(Text, nullable=True)
    is_selected = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
