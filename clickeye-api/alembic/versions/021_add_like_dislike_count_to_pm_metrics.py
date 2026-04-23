"""pm_metrics 테이블에 like_count, dislike_count 컬럼 추가

Revision ID: 021
Revises: 020
Create Date: 2026-04-23 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "pm_metrics",
        sa.Column("like_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pm_metrics",
        sa.Column("dislike_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("pm_metrics", "dislike_count")
    op.drop_column("pm_metrics", "like_count")
