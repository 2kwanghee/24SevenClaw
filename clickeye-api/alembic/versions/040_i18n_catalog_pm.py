"""카탈로그/PM 프로필 영문 컬럼 추가 (i18n Phase 3).

agents/skills/mcp_servers/hooks 테이블에 name_en, description_en, body_md_en 컬럼 추가.
pm_profiles 테이블에 name_en, title_en, description_en, bio_long_en 컬럼 추가.
기존 한국어 컬럼은 보존하여 fallback으로 사용한다.

Revision ID: 040
Revises: 039
Create Date: 2026-05-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "040"
down_revision: str | None = "039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REGISTRY_TABLES = ("agents", "skills", "mcp_servers", "hooks")


def upgrade() -> None:
    # ─── registry 테이블 (agents / skills / mcp_servers / hooks) ───
    for table in _REGISTRY_TABLES:
        op.add_column(table, sa.Column("name_en", sa.String(length=200), nullable=True))
        op.add_column(table, sa.Column("description_en", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("body_md_en", sa.Text(), nullable=True))

    # ─── pm_profiles ───
    op.add_column("pm_profiles", sa.Column("name_en", sa.String(length=100), nullable=True))
    op.add_column("pm_profiles", sa.Column("title_en", sa.String(length=200), nullable=True))
    op.add_column("pm_profiles", sa.Column("description_en", sa.Text(), nullable=True))
    op.add_column("pm_profiles", sa.Column("bio_long_en", sa.Text(), nullable=True))


def downgrade() -> None:
    # ─── pm_profiles ───
    for col in ("bio_long_en", "description_en", "title_en", "name_en"):
        op.drop_column("pm_profiles", col)

    # ─── registry 테이블 ───
    for table in _REGISTRY_TABLES:
        for col in ("body_md_en", "description_en", "name_en"):
            op.drop_column(table, col)
