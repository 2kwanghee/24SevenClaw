"""중앙 계약 관리 모델.

CentralContract: 중앙에서 관리하는 실행 계약 정의
CustomerContractOverride: 고객 프로젝트별 허용 필드 오버라이드
ContractAuditLog: 계약 변경 감사 로그
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String, Text, Uuid

from app.database import Base


class CentralContract(Base):
    """중앙 실행 계약 정의."""

    __tablename__ = "central_contracts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    contract_type = Column(String(50), nullable=False)
    source = Column(String(200), nullable=False)
    version = Column(String(50), nullable=False, default="1.0.0")
    content = Column(JSON, nullable=False, default=dict)
    description = Column(Text, nullable=True)
    is_locked = Column(Boolean, nullable=False, default=True)
    allowed_overrides = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class CustomerContractOverride(Base):
    """고객 프로젝트별 계약 오버라이드."""

    __tablename__ = "customer_contract_overrides"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    central_contract_id = Column(
        Uuid,
        ForeignKey("central_contracts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    override_content = Column(JSON, nullable=False, default=dict)
    approved_by = Column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class ContractAuditLog(Base):
    """계약 변경 감사 로그."""

    __tablename__ = "contract_audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    contract_id = Column(
        Uuid,
        ForeignKey("central_contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    override_id = Column(
        Uuid,
        ForeignKey("customer_contract_overrides.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    change_type = Column(String(50), nullable=False)
    diff_snapshot = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
