"""projects 테이블에 부트스트랩 컬럼 추가

Revision ID: 030
Revises: 029
Create Date: 2026-04-29
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("requirements_text", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("setup_token_hash", sa.String(128), nullable=True))
    op.add_column(
        "projects",
        sa.Column(
            "bootstrap_status",
            sa.String(32),
            nullable=False,
            server_default="skipped",
        ),
    )
    op.add_column(
        "projects",
        sa.Column("bootstrap_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "bootstrap_completed_at")
    op.drop_column("projects", "bootstrap_status")
    op.drop_column("projects", "setup_token_hash")
    op.drop_column("projects", "requirements_text")
