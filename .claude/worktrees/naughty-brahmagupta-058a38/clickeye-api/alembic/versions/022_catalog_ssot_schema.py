"""카탈로그 DB-SSOT 전환 — agents/skills 컬럼 확장 + hooks 테이블 생성

Revision ID: 022
Revises: 021
Create Date: 2026-04-23 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # agents 테이블 신규 컬럼
    op.add_column("agents", sa.Column("required", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("agents", sa.Column("output_file", sa.String(200), nullable=True))
    op.add_column("agents", sa.Column("dependencies", postgresql.JSONB(), nullable=False, server_default="[]"))

    # skills 테이블 신규 컬럼
    op.add_column("skills", sa.Column("required", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("skills", sa.Column("output_file", sa.String(200), nullable=True))
    op.add_column("skills", sa.Column("dependencies", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("skills", sa.Column("hook_events", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("skills", sa.Column("env_vars", postgresql.JSONB(), nullable=False, server_default="[]"))

    # hooks 테이블 신규 생성
    op.create_table(
        "hooks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("body_md", sa.Text(), nullable=True),
        sa.Column("event", sa.String(50), nullable=False, server_default="PostToolUse"),
        sa.Column("version", sa.String(50), nullable=False, server_default="0.1.0"),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("output_file", sa.String(200), nullable=True),
        sa.Column("config_schema", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("hooks")
    op.drop_column("skills", "env_vars")
    op.drop_column("skills", "hook_events")
    op.drop_column("skills", "dependencies")
    op.drop_column("skills", "output_file")
    op.drop_column("skills", "required")
    op.drop_column("agents", "dependencies")
    op.drop_column("agents", "output_file")
    op.drop_column("agents", "required")
