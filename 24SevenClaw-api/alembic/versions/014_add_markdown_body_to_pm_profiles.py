"""pm_profiles 테이블에 markdown_body 컬럼 추가

Revision ID: 014
Revises: 013
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pm_profiles", sa.Column("markdown_body", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("pm_profiles", "markdown_body")
