"""SQLAlchemy 모델 Mixin — UUID PK + 타임스탬프 공통 컬럼.

declared_attr 없이 단순 Column 할당으로 정의한다.
SQLAlchemy 2.0 DeclarativeBase는 Mixin 내의 Column 객체를 상속 시점에 자동으로 복사한다.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Uuid


class UUIDPKMixin:
    """UUID 기본키 컬럼을 제공하는 Mixin."""

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """created_at / updated_at 타임스탬프 컬럼을 제공하는 Mixin."""

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
