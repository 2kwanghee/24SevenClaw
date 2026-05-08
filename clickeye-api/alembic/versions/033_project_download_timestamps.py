"""프로젝트 ZIP/env 다운로드 시각 컬럼 추가 — 키 staleness 판정용

Revision ID: 033
Revises: 032
Create Date: 2026-05-08
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("last_zip_downloaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("last_env_downloaded_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "last_env_downloaded_at")
    op.drop_column("projects", "last_zip_downloaded_at")
