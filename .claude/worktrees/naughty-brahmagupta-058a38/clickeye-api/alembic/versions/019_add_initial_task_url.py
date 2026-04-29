"""projects 테이블에 initial_task_url 컬럼 추가

Revision ID: 019
Revises: 018
Create Date: 2026-04-22 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("initial_task_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "initial_task_url")
