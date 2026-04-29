from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSON

from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    updated_by = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
