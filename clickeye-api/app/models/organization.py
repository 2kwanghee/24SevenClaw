from sqlalchemy import JSON, Column, ForeignKey, String, Text, Uuid

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Organization(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    company_name = Column(String(200), nullable=False)
    size = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)
    tech_stack = Column(JSON, nullable=True)
    main_product = Column(String(500), nullable=True)
    business_type = Column(String(100), nullable=True)
    company_description = Column(Text, nullable=True)

    # 컨트롤 타워: 자사(internal) vs 고객사(customer) 구분
    org_type = Column(String(20), nullable=False, default="customer", server_default="customer")
    # 담당 PM (ClickEye 내부 직원)
    account_manager_id = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # 고객사 운영 상태: active | paused | archived
    customer_status = Column(String(20), nullable=False, default="active", server_default="active")
    # 조직별 기능 플래그 JSONB — 예: {"live_preview_enabled": true}
    features = Column(JSON, nullable=False, default=dict, server_default="{}")
