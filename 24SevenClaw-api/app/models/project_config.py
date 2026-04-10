import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Uuid

from app.database import Base


class ProjectConfig(Base):
    __tablename__ = "project_configs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_type = Column(String(20), nullable=False)  # "agent", "skill", "mcp"
    agent_id = Column(
        Uuid, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    skill_id = Column(
        Uuid, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True
    )
    mcp_server_id = Column(
        Uuid, ForeignKey("mcp_servers.id", ondelete="SET NULL"), nullable=True
    )
    config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
