from sqlalchemy import JSON, Column, String, Text

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Organization(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    company_name = Column(String(200), nullable=False)
    size = Column(String(50), nullable=True)  # e.g. "1-10", "11-50", "51-200", "201-1000", "1000+"
    industry = Column(String(100), nullable=True)
    tech_stack = Column(JSON, nullable=True)  # e.g. ["Python", "React", "PostgreSQL"]
    main_product = Column(String(500), nullable=True)
    business_type = Column(String(100), nullable=True)
    company_description = Column(Text, nullable=True)
