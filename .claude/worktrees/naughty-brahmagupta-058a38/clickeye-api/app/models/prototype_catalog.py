"""프로토타입 카탈로그 모델 — 관리자가 CRUD 가능한 DB 기반 카탈로그."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text, Uuid

from app.database import Base


class PrototypeCatalogEntry(Base):
    """프로토타입 카탈로그 엔트리.

    위저드에서 사용자에게 제안하는 프로토타입의 원본 데이터.
    Claude API 사용 시 RAG 참조 자료, 미사용 시 태그 매칭 폴백으로 활용.
    """

    __tablename__ = "prototype_catalog_entries"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    slug = Column(String(200), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)

    # 분류 (태그 기반 — 고정 enum 아님)
    tags = Column(JSON, nullable=False, default=list)           # ["saas", "fullstack"]
    primary_tag = Column(String(100), nullable=True, index=True) # 대표 태그

    # 아키텍처 정보
    design_pattern = Column(String(100), nullable=True)         # "saas-fullstack"
    architecture_pattern = Column(String(200), nullable=True)   # "모놀리식 3-tier"
    tech_stack_tags = Column(JSON, nullable=False, default=list) # ["Next.js", "FastAPI"]

    # 사용자 표시 정보
    pros = Column(JSON, nullable=False, default=list)
    cons = Column(JSON, nullable=False, default=list)
    ui_structure = Column(JSON, nullable=False, default=dict)
    menu_structure = Column(JSON, nullable=False, default=dict)
    color_palette = Column(JSON, nullable=False, default=dict)

    # Agent 컨텍스트 (24S-199 에픽: 프로토타입 → Agent 구현 컨텍스트 연동)
    design_philosophy = Column(Text, nullable=True)
    implementation_constraints = Column(JSON, nullable=False, default=list)
    recommended_agents = Column(JSON, nullable=False, default=list)
    optional_agents = Column(JSON, nullable=False, default=list)
    excluded_agents = Column(JSON, nullable=False, default=list)
    recommended_skills = Column(JSON, nullable=False, default=list)
    agent_strategy = Column(Text, nullable=True)
    task_distribution_guide = Column(Text, nullable=True)

    # 메타
    is_active = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=0)  # 동일 태그 내 정렬
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class PrototypeTag(Base):
    """프로토타입 분류 태그 — 관리자가 자유롭게 추가/수정 가능."""

    __tablename__ = "prototype_tags"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    label = Column(String(100), nullable=False)      # "SaaS"
    label_ko = Column(String(100), nullable=True)    # "SaaS 플랫폼"
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)        # "#3B82F6"
    is_active = Column(Boolean, nullable=False, default=True)
    sort_order = Column(Integer, nullable=False, default=0)
