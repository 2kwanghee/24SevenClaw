"""ROI 표준 단가/공수 파라미터 모델."""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class RoiCategory(StrEnum):
    role_rate = "role_rate"
    solution_effort = "solution_effort"
    complexity_multiplier = "complexity_multiplier"


class RoiStandard(Base):
    __tablename__ = "roi_standards"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    category = Column(Enum(RoiCategory, name="roi_category"), nullable=False, index=True)
    key = Column(String(64), nullable=False)
    label = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    value_numeric = Column(Numeric(14, 2), nullable=True)
    value_json = Column(JSONB, nullable=True)
    unit = Column(String(32), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    updated_by = Column(Uuid, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (UniqueConstraint("category", "key", name="uq_roi_standard_cat_key"),)
