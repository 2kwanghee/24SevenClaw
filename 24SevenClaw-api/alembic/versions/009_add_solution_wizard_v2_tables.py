"""Solution Wizard v2 테이블 추가 (프로토타입 세션, PM 프로필 등)

Revision ID: 009
Revises: 008
Create Date: 2026-04-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "009"
down_revision: str = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- 신규 테이블: prototype_sessions ---
    op.create_table(
        "prototype_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("user_input", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_prototype_sessions_organization_id", "prototype_sessions", ["organization_id"]
    )
    op.create_index("ix_prototype_sessions_user_id", "prototype_sessions", ["user_id"])

    # --- 신규 테이블: prototypes ---
    op.create_table(
        "prototypes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("solution_type", sa.String(50), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["prototype_sessions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_prototypes_session_id", "prototypes", ["session_id"])

    # --- 신규 테이블: pm_profiles ---
    op.create_table(
        "pm_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("specialty", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=False),
        sa.Column("experience_areas", sa.JSON(), nullable=False),
        sa.Column("personality_traits", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_pm_profiles_slug", "pm_profiles", ["slug"])

    # --- 신규 테이블: pm_compositions ---
    op.create_table(
        "pm_compositions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("prototype_id", sa.Uuid(), nullable=False),
        sa.Column("pm_profile_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("assigned_agents", sa.JSON(), nullable=False),
        sa.Column("assigned_skills", sa.JSON(), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["prototype_id"],
            ["prototypes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pm_profile_id"],
            ["pm_profiles.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_pm_compositions_prototype_id", "pm_compositions", ["prototype_id"])
    op.create_index("ix_pm_compositions_pm_profile_id", "pm_compositions", ["pm_profile_id"])

    # --- 신규 테이블: pm_metrics ---
    op.create_table(
        "pm_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pm_profile_id", sa.Uuid(), nullable=False),
        sa.Column("total_projects", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("avg_rating", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pm_profile_id"),
        sa.ForeignKeyConstraint(
            ["pm_profile_id"],
            ["pm_profiles.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_pm_metrics_pm_profile_id", "pm_metrics", ["pm_profile_id"])

    # --- 신규 테이블: pm_ratings ---
    op.create_table(
        "pm_ratings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pm_profile_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["pm_profile_id"],
            ["pm_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_pm_ratings_pm_profile_id", "pm_ratings", ["pm_profile_id"])
    op.create_index("ix_pm_ratings_project_id", "pm_ratings", ["project_id"])
    op.create_index("ix_pm_ratings_user_id", "pm_ratings", ["user_id"])

    # --- 기존 테이블 확장: organizations ---
    op.add_column("organizations", sa.Column("main_product", sa.String(500), nullable=True))
    op.add_column("organizations", sa.Column("business_type", sa.String(20), nullable=True))
    op.add_column("organizations", sa.Column("company_description", sa.Text(), nullable=True))

    # --- 기존 테이블 확장: projects ---
    op.add_column("projects", sa.Column("prototype_session_id", sa.Uuid(), nullable=True))
    op.add_column("projects", sa.Column("pm_profile_id", sa.Uuid(), nullable=True))
    op.add_column("projects", sa.Column("project_type", sa.String(50), nullable=True))
    op.create_foreign_key(
        "fk_projects_prototype_session_id",
        "projects",
        "prototype_sessions",
        ["prototype_session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_projects_pm_profile_id",
        "projects",
        "pm_profiles",
        ["pm_profile_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_projects_prototype_session_id", "projects", ["prototype_session_id"])
    op.create_index("ix_projects_pm_profile_id", "projects", ["pm_profile_id"])


def downgrade() -> None:
    # --- projects 컬럼 제거 ---
    op.drop_index("ix_projects_pm_profile_id", table_name="projects")
    op.drop_index("ix_projects_prototype_session_id", table_name="projects")
    op.drop_constraint("fk_projects_pm_profile_id", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_prototype_session_id", "projects", type_="foreignkey")
    op.drop_column("projects", "project_type")
    op.drop_column("projects", "pm_profile_id")
    op.drop_column("projects", "prototype_session_id")

    # --- organizations 컬럼 제거 ---
    op.drop_column("organizations", "company_description")
    op.drop_column("organizations", "business_type")
    op.drop_column("organizations", "main_product")

    # --- 신규 테이블 제거 (역순) ---
    op.drop_table("pm_ratings")
    op.drop_table("pm_metrics")
    op.drop_table("pm_compositions")
    op.drop_table("pm_profiles")
    op.drop_table("prototypes")
    op.drop_table("prototype_sessions")
