import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, Uuid

from app.database import Base


class UserLinearCredentials(Base):
    __tablename__ = "user_linear_credentials"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    encrypted_api_key = Column(Text, nullable=False)
    team_id = Column(String(100), nullable=False)
    webhook_secret = Column(String(200), nullable=True)
    tunnel_url = Column(String(500), nullable=True)
    linear_webhook_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
