"""PM 관리 확장 및 추천 로그 테이블 추가

Revision ID: 012
Revises: 011
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "012"
down_revision: str | None = "c255febcea16"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- pm_profiles 컬럼 확장 ---
    op.add_column(
        "pm_profiles",
        sa.Column("bio_long", sa.Text(), nullable=True),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("years_experience", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pm_profiles",
        sa.Column(
            "preferred_solution_types",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "pm_profiles",
        sa.Column(
            "tech_stack_tags",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "pm_profiles",
        sa.Column(
            "industry_tags",
            sa.JSON(),
            nullable=False,
            server_default="[]",
        ),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("language", sa.String(8), nullable=False, server_default="ko"),
    )
    op.add_column(
        "pm_profiles",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # --- pm_recommendation_logs 테이블 생성 ---
    op.create_table(
        "pm_recommendation_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("input_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("claude_raw", sa.JSON(), nullable=True),
        sa.Column("final_ranking", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("selected_pm_id", sa.Uuid(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "is_fallback", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["prototype_sessions.id"],
            name="fk_pm_rec_logs_session_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pm_recommendation_logs_session_id",
        "pm_recommendation_logs",
        ["session_id"],
    )
    op.create_index(
        "ix_pm_recommendation_logs_created_at",
        "pm_recommendation_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_pm_recommendation_logs_created_at",
        table_name="pm_recommendation_logs",
    )
    op.drop_index(
        "ix_pm_recommendation_logs_session_id",
        table_name="pm_recommendation_logs",
    )
    op.drop_table("pm_recommendation_logs")

    op.drop_column("pm_profiles", "updated_at")
    op.drop_column("pm_profiles", "language")
    op.drop_column("pm_profiles", "industry_tags")
    op.drop_column("pm_profiles", "tech_stack_tags")
    op.drop_column("pm_profiles", "preferred_solution_types")
    op.drop_column("pm_profiles", "years_experience")
    op.drop_column("pm_profiles", "bio_long")
