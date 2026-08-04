import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Uuid, text

from app.database import Base


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    # 활성 멤버십 부분 유니크 인덱스 — 마이그레이션 047 이 만든 것과 정확히 일치시킨다
    # (모델이 선언하지 않으면 autogenerate 가 "지워야 할 인덱스" 로 보고 drop_index 를 낸다).
    # postgresql_where 는 실 DB(PG)와의 정합용, sqlite_where 는 테스트 create_all 에서 전체
    # 유니크가 아닌 부분 인덱스로 만들어 비활성 이력 행 중복이 깨지지 않게 한다.
    __table_args__ = (
        Index(
            "uq_org_membership_active",
            "user_id",
            "organization_id",
            unique=True,
            postgresql_where=text("is_active"),
            sqlite_where=text("is_active"),
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_role = Column(String(20), nullable=False, server_default="org_member")
    invited_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    is_active = Column(Boolean, default=True)


class RoleAuditLog(Base):
    __tablename__ = "role_audit_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    target_user_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)
    old_value = Column(String(100), nullable=True)
    new_value = Column(String(100), nullable=False)
    resource = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
