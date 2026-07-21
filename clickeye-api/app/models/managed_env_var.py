"""관리형 환경변수 테이블 (CE-305 PR-3, superadmin 전용).

value_encrypted 컬럼에 Fernet(app.core.crypto) 암호화된 env 값을 저장한다.
평문은 DB 에 절대 저장하지 않으며, 렌더/조회 시점에만 복호화한다.
편집 제외 키(JWT_SECRET_KEY/DATABASE_URL/REDIS_URL)는 이 테이블에 저장되지 않는다
(정책은 env_service 에서 강제).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text, Uuid

from app.database import Base


class ManagedEnvVar(Base):
    __tablename__ = "managed_env_vars"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    # env 변수명 (예: CORS_ORIGINS). allowlist 로 제한.
    key = Column(String(128), nullable=False, unique=True)
    # Fernet 암호화된 값 (복호화 전까지 평문 아님).
    value_encrypted = Column(Text, nullable=False)
    # 시크릿 여부 — True 면 조회 시 값을 마스킹/미반환.
    is_secret = Column(Boolean, nullable=False, default=False)
    # 마지막으로 변경한 superadmin (감사 보조). users FK 는 걸지 않음(느슨한 참조).
    updated_by = Column(Uuid, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
