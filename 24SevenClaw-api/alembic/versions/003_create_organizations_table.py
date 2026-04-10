"""organizations 테이블 생성 및 users.organization_id FK 추가

Revision ID: 003
Revises: 002
Create Date: 2026-04-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("size", sa.String(50), nullable=True),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("tech_stack", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "users",
        sa.Column(
            "organization_id",
            postgresql.UUID(),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "organization_id")
    op.drop_table("organizations")
