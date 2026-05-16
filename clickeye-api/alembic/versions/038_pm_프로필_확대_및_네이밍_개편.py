"""PM 프로필 확대 및 네이밍 개편 — 기존 8종 한국어 명 변경 + 신규 12종 추가.

Revision ID: 038
Revises: 037
Create Date: 2026-05-14
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa

from alembic import op

revision: str = "038"
down_revision: str | None = "037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ── 기존 PM 업데이트 ──────────────────────────────────────────────────────────

_UPDATES = [
    {
        "slug": "atlas",
        "name": "백엔드 설계 PM",
        "tech_stack_tags": ["Python", "Go", "PostgreSQL", "Redis", "Kafka"],
        "industry_tags": ["it", "fintech", "금융/핀테크", "saas"],
    },
    {
        "slug": "bridge",
        "name": "API 연동 PM",
        "tech_stack_tags": ["TypeScript", "Python", "REST", "GraphQL", "Webhook"],
        "industry_tags": ["it", "ecommerce", "이커머스", "logistics", "물류/배송"],
    },
    {
        "slug": "forge",
        "name": "데이터 엔지니어링 PM",
        "tech_stack_tags": ["Python", "Spark", "Airflow", "PostgreSQL", "Elasticsearch"],
        "industry_tags": ["it", "finance", "금융", "manufacturing", "제조업"],
    },
    {
        "slug": "nova",
        "name": "풀스택 PM",
        "tech_stack_tags": ["TypeScript", "React", "Next.js", "FastAPI", "PostgreSQL"],
        "industry_tags": ["it", "startup", "스타트업"],
    },
    {
        "slug": "pixel",
        "name": "프론트엔드 PM",
        "tech_stack_tags": ["TypeScript", "React", "Next.js", "Tailwind CSS", "Figma"],
        "industry_tags": ["it", "ecommerce", "이커머스", "game", "게임"],
    },
    {
        "slug": "sentinel",
        "name": "DevOps/인프라 PM",
        "tech_stack_tags": ["Docker", "Kubernetes", "AWS", "Terraform", "GitHub Actions"],
        "industry_tags": ["it", "enterprise", "엔터프라이즈"],
    },
    {
        "slug": "shield",
        "name": "보안 PM",
        "tech_stack_tags": ["Python", "TypeScript", "OAuth2", "JWT", "OWASP"],
        "industry_tags": ["fintech", "금융/핀테크", "healthcare", "헬스케어", "enterprise", "엔터프라이즈"],
    },
    {
        "slug": "spark",
        "name": "MVP 빠른 출시 PM",
        "tech_stack_tags": ["TypeScript", "React", "FastAPI", "SQLite", "Vercel"],
        "industry_tags": ["startup", "스타트업", "b2c"],
    },
]

# ── 신규 PM 12종 ──────────────────────────────────────────────────────────────

_NEW_PMS = [
    {
        "slug": "ledger",
        "name": "핀테크/결제 PM",
        "title": "금융 서비스 & 결제 시스템 전문가",
        "description": "결제·KYC·오픈뱅킹 설계에 특화된 핀테크 전문 PM",
        "domain": "fintech",
        "specialties": [
            "payment-system",
            "kyc-aml",
            "open-banking",
            "fraud-detection",
            "subscription-billing",
            "financial-reporting",
        ],
        "tech_stack_tags": ["Python", "TypeScript", "PostgreSQL", "Redis", "Stripe"],
        "industry_tags": ["fintech", "금융/핀테크", "b2b", "b2c"],
    },
    {
        "slug": "commerce",
        "name": "이커머스 PM",
        "title": "쇼핑 플랫폼 & 주문 관리 전문가",
        "description": "상품 카탈로그·주문·검색·추천 시스템을 아우르는 이커머스 PM",
        "domain": "ecommerce",
        "specialties": [
            "product-catalog",
            "cart-checkout",
            "order-fulfillment",
            "search-ranking",
            "recommendation-engine",
            "seller-portal",
        ],
        "tech_stack_tags": ["TypeScript", "React", "PostgreSQL", "Elasticsearch", "Redis"],
        "industry_tags": ["ecommerce", "이커머스/리테일", "b2c", "b2b2c"],
    },
    {
        "slug": "medic",
        "name": "헬스케어 PM",
        "title": "의료 시스템 & 디지털 헬스 전문가",
        "description": "EMR 연동·원격진료·HIPAA 컴플라이언스 설계 전문 PM",
        "domain": "healthcare",
        "specialties": [
            "ehr-integration",
            "telemedicine",
            "hipaa-compliance",
            "appointment-scheduling",
            "medical-billing",
            "patient-portal",
        ],
        "tech_stack_tags": ["TypeScript", "Python", "PostgreSQL", "HL7-FHIR"],
        "industry_tags": ["healthcare", "헬스케어/의료", "b2c", "b2b"],
    },
    {
        "slug": "swift",
        "name": "모바일 앱 PM",
        "title": "크로스플랫폼 모바일 앱 전문가",
        "description": "iOS/Android 크로스플랫폼·오프라인 동기화·푸시 알림 전문 PM",
        "domain": "mobile",
        "specialties": [
            "cross-platform-mobile",
            "push-notification",
            "offline-sync",
            "deep-linking",
            "mobile-payment",
            "app-store-optimization",
        ],
        "tech_stack_tags": ["TypeScript", "React Native", "Flutter", "Firebase"],
        "industry_tags": ["it", "ecommerce", "이커머스", "game", "게임"],
    },
    {
        "slug": "cortex",
        "name": "AI 통합 PM",
        "title": "LLM & AI 워크플로 설계 전문가",
        "description": "LLM 연동·RAG 파이프라인·벡터 검색 설계에 특화된 AI PM",
        "domain": "ai",
        "specialties": [
            "llm-integration",
            "rag-pipeline",
            "vector-search",
            "prompt-engineering",
            "ai-workflow",
            "model-serving",
        ],
        "tech_stack_tags": ["Python", "TypeScript", "PostgreSQL", "pgvector", "LangChain"],
        "industry_tags": ["it", "education", "교육/에듀테크", "marketing", "마케팅"],
    },
    {
        "slug": "prism",
        "name": "B2B SaaS PM",
        "title": "멀티테넌트 SaaS 플랫폼 전문가",
        "description": "멀티테넌시·구독 과금·온보딩 플로우 설계 전문 PM",
        "domain": "saas",
        "specialties": [
            "multi-tenancy",
            "subscription-billing",
            "role-based-access",
            "onboarding-flow",
            "usage-metering",
            "white-label",
        ],
        "tech_stack_tags": ["TypeScript", "React", "PostgreSQL", "Stripe", "Auth.js"],
        "industry_tags": ["it", "saas", "b2b"],
    },
    {
        "slug": "nexus",
        "name": "마켓플레이스 PM",
        "title": "양면 시장 플랫폼 전문가",
        "description": "공급자-소비자 매칭·에스크로·수수료 모델 설계 전문 PM",
        "domain": "marketplace",
        "specialties": [
            "two-sided-marketplace",
            "matching-algorithm",
            "escrow-payment",
            "review-rating",
            "seller-onboarding",
            "commission-model",
        ],
        "tech_stack_tags": ["TypeScript", "Python", "PostgreSQL", "Elasticsearch", "Redis"],
        "industry_tags": ["ecommerce", "b2b2c"],
    },
    {
        "slug": "pulse",
        "name": "실시간 서비스 PM",
        "title": "WebSocket & 이벤트 스트리밍 전문가",
        "description": "채팅·라이브 협업·실시간 알림 시스템 설계 전문 PM",
        "domain": "realtime",
        "specialties": [
            "websocket-design",
            "event-streaming",
            "push-notification",
            "live-collaboration",
            "presence-system",
            "chat-messaging",
        ],
        "tech_stack_tags": ["TypeScript", "Go", "Redis", "PostgreSQL", "WebSocket"],
        "industry_tags": ["it", "game", "b2c"],
    },
    {
        "slug": "vision",
        "name": "데이터 분석 PM",
        "title": "BI 대시보드 & KPI 분석 전문가",
        "description": "대시보드·KPI·코호트 분석 설계에 특화된 애널리틱스 PM",
        "domain": "analytics",
        "specialties": [
            "dashboard-design",
            "data-visualization",
            "kpi-tracking",
            "funnel-analysis",
            "cohort-analysis",
            "report-automation",
        ],
        "tech_stack_tags": ["TypeScript", "Python", "PostgreSQL", "Grafana", "Metabase"],
        "industry_tags": ["it", "marketing", "enterprise"],
    },
    {
        "slug": "ops",
        "name": "내부 도구 PM",
        "title": "어드민 & 운영 자동화 전문가",
        "description": "사내 어드민 패널·워크플로 자동화·권한 관리 설계 전문 PM",
        "domain": "internal",
        "specialties": [
            "admin-panel",
            "workflow-automation",
            "role-management",
            "audit-logging",
            "bulk-operations",
            "integration-hub",
        ],
        "tech_stack_tags": ["TypeScript", "React", "PostgreSQL", "Python"],
        "industry_tags": ["it", "enterprise", "엔터프라이즈", "manufacturing", "제조업"],
    },
    {
        "slug": "arena",
        "name": "게임 서비스 PM",
        "title": "게임 백엔드 & 라이브 서비스 전문가",
        "description": "게임 루프·리더보드·매칭·IAP 설계에 특화된 게임 서비스 PM",
        "domain": "game",
        "specialties": [
            "game-loop",
            "leaderboard-ranking",
            "in-app-purchase",
            "anti-cheat",
            "matchmaking",
            "social-features",
        ],
        "tech_stack_tags": ["TypeScript", "Go", "Redis", "PostgreSQL", "Unity"],
        "industry_tags": ["game", "게임/엔터테인먼트", "b2c"],
    },
    {
        "slug": "route",
        "name": "물류/배송 PM",
        "title": "배송 추적 & 물류 최적화 전문가",
        "description": "경로 최적화·배송 추적·창고 관리 시스템 설계 전문 PM",
        "domain": "logistics",
        "specialties": [
            "route-optimization",
            "tracking-system",
            "warehouse-management",
            "carrier-integration",
            "delivery-scheduling",
            "inventory-sync",
        ],
        "tech_stack_tags": ["Python", "TypeScript", "PostgreSQL", "Redis", "Google Maps API"],
        "industry_tags": ["logistics", "물류/배송", "b2b", "b2c"],
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # 1. 기존 PM 이름·태그 업데이트
    for pm in _UPDATES:
        conn.execute(
            sa.text(
                """
                UPDATE pm_profiles
                SET name = :name,
                    tech_stack_tags = cast(:tech_stack_tags as json),
                    industry_tags   = cast(:industry_tags as json),
                    updated_at      = :now
                WHERE slug = :slug
                """
            ),
            {
                "slug": pm["slug"],
                "name": pm["name"],
                "tech_stack_tags": json.dumps(pm["tech_stack_tags"], ensure_ascii=False),
                "industry_tags": json.dumps(pm["industry_tags"], ensure_ascii=False),
                "now": now,
            },
        )

    # 2. 신규 PM 삽입 (이미 존재하면 이름·태그만 upsert)
    for pm in _NEW_PMS:
        existing = conn.execute(
            sa.text("SELECT id FROM pm_profiles WHERE slug = :slug"),
            {"slug": pm["slug"]},
        ).fetchone()

        if existing:
            conn.execute(
                sa.text(
                    """
                    UPDATE pm_profiles
                    SET name            = :name,
                        title           = :title,
                        description     = :description,
                        domain          = :domain,
                        specialties     = cast(:specialties as json),
                        tech_stack_tags = cast(:tech_stack_tags as json),
                        industry_tags   = cast(:industry_tags as json),
                        updated_at      = :now
                    WHERE slug = :slug
                    """
                ),
                {
                    "slug": pm["slug"],
                    "name": pm["name"],
                    "title": pm["title"],
                    "description": pm["description"],
                    "domain": pm["domain"],
                    "specialties": json.dumps(pm["specialties"], ensure_ascii=False),
                    "tech_stack_tags": json.dumps(pm["tech_stack_tags"], ensure_ascii=False),
                    "industry_tags": json.dumps(pm["industry_tags"], ensure_ascii=False),
                    "now": now,
                },
            )
        else:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO pm_profiles (
                        id, slug, name, title, description, domain,
                        specialties, tech_stack_tags, industry_tags,
                        is_active, created_at, updated_at
                    ) VALUES (
                        :id, :slug, :name, :title, :description, :domain,
                        cast(:specialties as json),
                        cast(:tech_stack_tags as json),
                        cast(:industry_tags as json),
                        true, :now, :now
                    )
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "slug": pm["slug"],
                    "name": pm["name"],
                    "title": pm["title"],
                    "description": pm["description"],
                    "domain": pm["domain"],
                    "specialties": json.dumps(pm["specialties"], ensure_ascii=False),
                    "tech_stack_tags": json.dumps(pm["tech_stack_tags"], ensure_ascii=False),
                    "industry_tags": json.dumps(pm["industry_tags"], ensure_ascii=False),
                    "now": now,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()

    # 신규 PM 삭제
    new_slugs = [pm["slug"] for pm in _NEW_PMS]
    for slug in new_slugs:
        conn.execute(
            sa.text("DELETE FROM pm_profiles WHERE slug = :slug"),
            {"slug": slug},
        )

    # 기존 PM 이름 원복
    _ORIGINALS = {
        "atlas": "Atlas",
        "bridge": "Bridge",
        "forge": "Forge",
        "nova": "Nova",
        "pixel": "Pixel",
        "sentinel": "Sentinel",
        "shield": "Shield",
        "spark": "Spark",
    }
    for slug, original_name in _ORIGINALS.items():
        conn.execute(
            sa.text("UPDATE pm_profiles SET name = :name WHERE slug = :slug"),
            {"slug": slug, "name": original_name},
        )
