import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, String, Text, Uuid

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    company_name = Column(String(200), nullable=False)
    size = Column(String(50), nullable=True)  # e.g. "1-10", "11-50", "51-200", "201-1000", "1000+"
    industry = Column(String(100), nullable=True)
    tech_stack = Column(JSON, nullable=True)  # e.g. ["Python", "React", "PostgreSQL"]
    main_product = Column(String(500), nullable=True)
    business_type = Column(String(20), nullable=True)  # b2b | b2c | internal
    company_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
