import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Uuid

from app.database import Base


class AgentConnection(Base):
    __tablename__ = "agent_connections"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    license_id = Column(
        Uuid, ForeignKey("licenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_token = Column(String(255), unique=True, nullable=False, index=True)
    hostname = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    status = Column(String(20), nullable=False, default="disconnected")
    last_heartbeat_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    connected_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
