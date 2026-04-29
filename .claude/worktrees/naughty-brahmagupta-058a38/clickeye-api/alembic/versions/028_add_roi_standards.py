"""roi_standards 테이블 추가

Revision ID: 028
Revises: 027
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE roi_category AS ENUM ('role_rate', 'solution_effort', 'complexity_multiplier')")
    op.create_table(
        "roi_standards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category", postgresql.ENUM("role_rate", "solution_effort", "complexity_multiplier", name="roi_category", create_type=False), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("value_numeric", sa.Numeric(14, 2), nullable=True),
        sa.Column("value_json", postgresql.JSONB(), nullable=True),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category", "key", name="uq_roi_standard_cat_key"),
    )
    op.create_index("ix_roi_standards_category", "roi_standards", ["category"])


def downgrade() -> None:
    op.drop_index("ix_roi_standards_category", table_name="roi_standards")
    op.drop_table("roi_standards")
    op.execute("DROP TYPE roi_category")
