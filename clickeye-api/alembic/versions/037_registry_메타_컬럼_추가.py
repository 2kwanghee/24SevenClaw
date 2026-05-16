"""agents/skills/hooks/mcp_servers 테이블에 tags·domains·compatible_pm_specialties 컬럼 추가.

Revision ID: 037
Revises: 036
Create Date: 2026-05-14
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "037"
down_revision: str | None = "036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("agents", "skills", "hooks", "mcp_servers")
_NEW_COLUMNS = (
    ("tags", sa.JSON(), "[]"),
    ("domains", sa.JSON(), "[]"),
    ("compatible_pm_specialties", sa.JSON(), "[]"),
)


def upgrade() -> None:
    for table in _TABLES:
        for col_name, col_type, default in _NEW_COLUMNS:
            op.add_column(
                table,
                sa.Column(
                    col_name,
                    col_type,
                    nullable=False,
                    server_default=default,
                ),
            )


def downgrade() -> None:
    for table in _TABLES:
        for col_name, _, _ in _NEW_COLUMNS:
            op.drop_column(table, col_name)
