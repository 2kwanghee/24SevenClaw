import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid, text

from app.database import Base


class UserAnthropicCredentials(Base):
    """사용자 Anthropic 자격증명 테이블.

    encrypted_api_key 컬럼에 Fernet 암호화된 비밀을 저장한다.
    credential_type 도메인:
      - api_key: Anthropic API 키(sk-ant-...) — in-API 호출/조직키 회계 경로
      - oauth_token: 구독 시트(다프로젝트화 P4) — `claude setup-token` 산출 OAuth 토큰.
        파이프라인이 CLAUDE_CODE_OAUTH_TOKEN 으로 주입해 실행한다.

    UniqueConstraint(user_id, credential_type) — 사용자당 시트 1개(본인 구독 계정)만
    허용한다(ToS 방어 패턴). api_key 행과 oauth_token 행은 type 이 달라 공존한다.
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
    # 구독 시트 상태 — active | exhausted | blocked. oauth_token 행에서만 의미가 있고
    # api_key 행에서는 무시된다(기본값 active 로 채워짐).
    seat_status = Column(
        String(16),
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
