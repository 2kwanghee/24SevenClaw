import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text, Uuid

from app.database import Base


class UserAnthropicCredentials(Base):
    __tablename__ = "user_anthropic_credentials"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    encrypted_api_key = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
