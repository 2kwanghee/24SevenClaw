"""projects 테이블에 wizard_data JSONB 컬럼 추가

Revision ID: 004
Revises: 003
Create Date: 2026-04-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("wizard_data", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "wizard_data")
