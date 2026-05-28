import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # 소셜 로그인 시 null
    display_name = Column(String(100), nullable=False)
    avatar_url = Column(String(500), nullable=True)
    plan = Column(String(20), default="free")
    system_role = Column(String(20), default="member", server_default="member", nullable=False)
    is_active = Column(Boolean, default=True)
    oauth_provider = Column(String(20), nullable=True)  # "github" | "google" | null
    oauth_id = Column(String(255), nullable=True)  # 외부 서비스 사용자 ID
    language = Column(String(8), default="en", server_default="en", nullable=False)
    organization_id = Column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
