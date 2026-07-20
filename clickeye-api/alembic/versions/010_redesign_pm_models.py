"""PM 모델 재설계 — 별도 파일 분리 및 필드 재구성

Revision ID: 010
Revises: 009
Create Date: 2026-04-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- pm_profiles 컬럼 재구성 ---
    # 기존 컬럼 제거
    op.drop_index("ix_pm_profiles_slug", table_name="pm_profiles")
    op.drop_column("pm_profiles", "specialty")
    op.drop_column("pm_profiles", "skills")
    op.drop_column("pm_profiles", "experience_areas")
    op.drop_column("pm_profiles", "personality_traits")

    # 신규 컬럼 추가
    op.add_column(
        "pm_profiles",
        sa.Column("title", sa.String(200), nullable=True),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("domain", sa.String(100), nullable=True),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("specialties", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("personality", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_pm_profiles_slug", "pm_profiles", ["slug"])

    # --- pm_compositions 테이블 재생성 ---
    op.drop_index("ix_pm_compositions_prototype_id", table_name="pm_compositions")
    op.drop_index("ix_pm_compositions_pm_profile_id", table_name="pm_compositions")
    op.drop_table("pm_compositions")

    op.create_table(
        "pm_compositions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pm_id", sa.Uuid(), nullable=False),
        sa.Column("component_type", sa.String(100), nullable=False),
        sa.Column("component_slug", sa.String(100), nullable=False),
        sa.Column("component_name", sa.String(200), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.ForeignKeyConstraint(
            ["pm_id"],
            ["pm_profiles.id"],
            name="fk_pm_compositions_pm_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pm_compositions_pm_id", "pm_compositions", ["pm_id"])

    # --- pm_metrics 컬럼 재구성 ---
    op.drop_index("ix_pm_metrics_pm_profile_id", table_name="pm_metrics")
    op.drop_constraint("uq_pm_metrics_pm_profile_id", "pm_metrics", type_="unique")
    op.drop_constraint("fk_pm_metrics_pm_profile_id", "pm_metrics", type_="foreignkey")
    op.drop_column("pm_metrics", "pm_profile_id")
    op.drop_column("pm_metrics", "total_projects")
    op.drop_column("pm_metrics", "updated_at")

    op.add_column(
        "pm_metrics",
        sa.Column("pm_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "pm_metrics",
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pm_metrics",
        sa.Column("completed_projects", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pm_metrics",
        sa.Column("total_ratings", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pm_metrics",
        sa.Column("avg_completion_days", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.create_foreign_key(
        "fk_pm_metrics_pm_id",
        "pm_metrics",
        "pm_profiles",
        ["pm_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint("uq_pm_metrics_pm_id", "pm_metrics", ["pm_id"])
    op.create_index("ix_pm_metrics_pm_id", "pm_metrics", ["pm_id"])

    # --- pm_ratings 테이블 재생성 ---
    op.drop_index("ix_pm_ratings_pm_profile_id", table_name="pm_ratings")
    op.drop_index("ix_pm_ratings_project_id", table_name="pm_ratings")
    op.drop_index("ix_pm_ratings_user_id", table_name="pm_ratings")
    op.drop_table("pm_ratings")

    op.create_table(
        "pm_ratings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pm_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["pm_id"],
            ["pm_profiles.id"],
            name="fk_pm_ratings_pm_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_pm_ratings_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["prototype_sessions.id"],
            name="fk_pm_ratings_session_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pm_ratings_pm_id", "pm_ratings", ["pm_id"])
    op.create_index("ix_pm_ratings_user_id", "pm_ratings", ["user_id"])
    op.create_index("ix_pm_ratings_session_id", "pm_ratings", ["session_id"])


def downgrade() -> None:
    # --- pm_ratings 복원 ---
    op.drop_index("ix_pm_ratings_session_id", table_name="pm_ratings")
    op.drop_index("ix_pm_ratings_user_id", table_name="pm_ratings")
    op.drop_index("ix_pm_ratings_pm_id", table_name="pm_ratings")
    op.drop_table("pm_ratings")

    op.create_table(
        "pm_ratings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pm_profile_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["pm_profile_id"],
            ["pm_profiles.id"],
            name="fk_pm_ratings_pm_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_pm_ratings_project_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_pm_ratings_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pm_ratings_pm_profile_id", "pm_ratings", ["pm_profile_id"])
    op.create_index("ix_pm_ratings_project_id", "pm_ratings", ["project_id"])
    op.create_index("ix_pm_ratings_user_id", "pm_ratings", ["user_id"])

    # --- pm_metrics 복원 ---
    op.drop_index("ix_pm_metrics_pm_id", table_name="pm_metrics")
    op.drop_constraint("uq_pm_metrics_pm_id", "pm_metrics", type_="unique")
    op.drop_constraint("fk_pm_metrics_pm_id", "pm_metrics", type_="foreignkey")
    op.drop_column("pm_metrics", "pm_id")
    op.drop_column("pm_metrics", "usage_count")
    op.drop_column("pm_metrics", "completed_projects")
    op.drop_column("pm_metrics", "total_ratings")
    op.drop_column("pm_metrics", "avg_completion_days")

    op.add_column(
        "pm_metrics",
        sa.Column("pm_profile_id", sa.Uuid(), nullable=False),
    )
    op.add_column(
        "pm_metrics",
        sa.Column("total_projects", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "pm_metrics",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_pm_metrics_pm_profile_id",
        "pm_metrics",
        "pm_profiles",
        ["pm_profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint("uq_pm_metrics_pm_profile_id", "pm_metrics", ["pm_profile_id"])
    op.create_index("ix_pm_metrics_pm_profile_id", "pm_metrics", ["pm_profile_id"])

    # --- pm_compositions 복원 ---
    op.drop_index("ix_pm_compositions_pm_id", table_name="pm_compositions")
    op.drop_table("pm_compositions")

    op.create_table(
        "pm_compositions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("prototype_id", sa.Uuid(), nullable=False),
        sa.Column("pm_profile_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("assigned_agents", sa.JSON(), nullable=False),
        sa.Column("assigned_skills", sa.JSON(), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["pm_profile_id"],
            ["pm_profiles.id"],
            name="fk_pm_compositions_pm_profile_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prototype_id"],
            ["prototypes.id"],
            name="fk_pm_compositions_prototype_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pm_compositions_prototype_id", "pm_compositions", ["prototype_id"])
    op.create_index("ix_pm_compositions_pm_profile_id", "pm_compositions", ["pm_profile_id"])

    # --- pm_profiles 컬럼 복원 ---
    op.drop_index("ix_pm_profiles_slug", table_name="pm_profiles")
    op.drop_column("pm_profiles", "title")
    op.drop_column("pm_profiles", "domain")
    op.drop_column("pm_profiles", "specialties")
    op.drop_column("pm_profiles", "personality")

    op.add_column(
        "pm_profiles",
        sa.Column("specialty", sa.String(50), nullable=False, server_default=""),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("skills", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("experience_areas", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "pm_profiles",
        sa.Column("personality_traits", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_pm_profiles_slug", "pm_profiles", ["slug"])
