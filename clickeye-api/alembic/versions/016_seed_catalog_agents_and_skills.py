"""카탈로그 기본 agents/skills seed 데이터 삽입 (멱등)

Revision ID: 016
Revises: 014, 015
Create Date: 2026-04-21 00:00:00.000000
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "016"
down_revision: str | tuple[str, ...] | None = ("014", "015")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOW = datetime(2026, 4, 21, tzinfo=UTC)

_AGENTS = [
    ("harness", "Harness", "코드 품질 게이트"),
    ("architect", "Architect", "시스템 설계"),
    ("frontend", "Frontend", "UI/UX 구현"),
    ("backend", "Backend", "API/서버"),
    ("qa", "QA", "테스트 자동화"),
    ("devops", "DevOps", "인프라/배포"),
    ("security", "Security", "보안 감사"),
]

_SKILLS = [
    ("linear", "Linear", "Linear 이슈 트래킹 연동"),
    ("telegram", "Telegram", "Telegram 봇 알림 연동"),
    ("github", "GitHub", "GitHub 리포지토리 연동"),
    ("slack", "Slack", "Slack 채널 알림 연동"),
    ("jira", "Jira", "Jira 이슈 트래킹 연동"),
    ("notion", "Notion", "Notion 워크스페이스 연동"),
]


def upgrade() -> None:
    conn = op.get_bind()

    for slug, name, description in _AGENTS:
        conn.execute(
            sa.text(
                """
                INSERT INTO agents (id, name, slug, description, version, is_public,
                                    config_schema, created_at, updated_at)
                VALUES (:id, :name, :slug, :description, '0.1.0', TRUE,
                        '{}', :now, :now)
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slug,
                "description": description,
                "now": _NOW,
            },
        )

    for slug, name, description in _SKILLS:
        conn.execute(
            sa.text(
                """
                INSERT INTO skills (id, name, slug, description, version, is_public,
                                    config_schema, created_at, updated_at)
                VALUES (:id, :name, :slug, :description, '0.1.0', TRUE,
                        '{}', :now, :now)
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slug,
                "description": description,
                "now": _NOW,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    agent_slugs = [slug for slug, _, _ in _AGENTS]
    skill_slugs = [slug for slug, _, _ in _SKILLS]

    conn.execute(
        sa.text("DELETE FROM agents WHERE slug = ANY(:slugs)"),
        {"slugs": agent_slugs},
    )
    conn.execute(
        sa.text("DELETE FROM skills WHERE slug = ANY(:slugs)"),
        {"slugs": skill_slugs},
    )
