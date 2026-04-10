"""에이전트/스킬/MCP 서버 레지스트리 모델 (우리 IP)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text, Uuid

from app.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="0.1.0")
    image_url = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    is_public = Column(Boolean, nullable=False, default=True)
    config_schema = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="0.1.0")
    image_url = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    is_public = Column(Boolean, nullable=False, default=True)
    config_schema = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False, default="0.1.0")
    image_url = Column(String(500), nullable=True)
    category = Column(String(50), nullable=True)
    is_public = Column(Boolean, nullable=False, default=True)
    config_schema = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
