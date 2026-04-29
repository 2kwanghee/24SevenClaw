import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Uuid,
)

from app.database import Base


class PMProfile(Base):
    __tablename__ = "pm_profiles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    avatar_url = Column(String(500), nullable=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    domain = Column(String(100), nullable=True)
    specialties = Column(JSON, nullable=False, default=list)
    personality = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    # Phase 3: PM 관리 확장 필드
    bio_long = Column(Text, nullable=True)
    years_experience = Column(Integer, nullable=True)
    preferred_solution_types = Column(JSON, nullable=False, default=list)
    tech_stack_tags = Column(JSON, nullable=False, default=list)
    industry_tags = Column(JSON, nullable=False, default=list)
    language = Column(String(8), nullable=False, default="ko")
    updated_at = Column(DateTime(timezone=True), nullable=True)
    markdown_body = Column(Text, nullable=True)
