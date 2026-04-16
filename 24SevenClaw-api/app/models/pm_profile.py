import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
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
    specialty = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    skills = Column(JSON, nullable=False, default=list)
    experience_areas = Column(JSON, nullable=False, default=list)
    personality_traits = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PMComposition(Base):
    __tablename__ = "pm_compositions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    prototype_id = Column(
        Uuid, ForeignKey("prototypes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pm_profile_id = Column(
        Uuid, ForeignKey("pm_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String(100), nullable=False)
    assigned_agents = Column(JSON, nullable=False, default=list)
    assigned_skills = Column(JSON, nullable=False, default=list)
    match_score = Column(Integer, nullable=False, default=0)
    reasoning = Column(Text, nullable=True)


class PMMetric(Base):
    __tablename__ = "pm_metrics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    pm_profile_id = Column(
        Uuid,
        ForeignKey("pm_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_projects = Column(Integer, nullable=False, default=0)
    success_rate = Column(Float, nullable=False, default=0.0)
    avg_rating = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PMRating(Base):
    __tablename__ = "pm_ratings"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    pm_profile_id = Column(
        Uuid, ForeignKey("pm_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score = Column(Integer, nullable=False)  # 1~5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
