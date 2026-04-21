"""프리셋 카탈로그 + 성숙도 평가 테이블 추가

Revision ID: 007
Revises: 006
Create Date: 2026-04-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: str = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "presets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("maturity_level", sa.String(20), nullable=False),
        sa.Column("solution_types", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_agents", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_skills", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("default_pipelines", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_presets_slug", "presets", ["slug"])
    op.create_index("ix_presets_maturity_level", "presets", ["maturity_level"])

    op.create_table(
        "maturity_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("recommended_preset_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recommended_preset_id"], ["presets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_maturity_assessments_user_id", "maturity_assessments", ["user_id"])
    op.create_index(
        "ix_maturity_assessments_organization_id", "maturity_assessments", ["organization_id"]
    )


def downgrade() -> None:
    op.drop_table("maturity_assessments")
    op.drop_table("presets")
