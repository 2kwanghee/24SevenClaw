import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, text

from app.database import Base


class UserAnthropicCredentials(Base):
    """사용자 Anthropic 자격증명 테이블.

    encrypted_api_key 컬럼에 Fernet 암호화된 API 키(sk-ant-...)를 저장.
    credential_type = "api_key" 고정.
    """

    __tablename__ = "user_anthropic_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "credential_type", name="uq_user_credential_type"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_type = Column(
        String(32),
        nullable=False,
        default="api_key",
        server_default=text("'api_key'"),
    )
    encrypted_api_key = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
