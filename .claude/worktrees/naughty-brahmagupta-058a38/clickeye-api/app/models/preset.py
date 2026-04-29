import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text, Uuid

from app.database import Base


class Preset(Base):
    __tablename__ = "presets"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    maturity_level = Column(String(20), nullable=False)  # starter | intermediate | advanced
    solution_types = Column(JSON, nullable=False, default=list)
    default_agents = Column(JSON, nullable=False, default=list)
    default_skills = Column(JSON, nullable=False, default=list)
    default_pipelines = Column(JSON, nullable=False, default=list)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
