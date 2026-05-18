"""Modernize 파이프라인 (MVP-2-A) 신규 테이블 5종 추가.

비침습성 원칙에 따라 기존 테이블은 어느 컬럼/인덱스/제약도 건드리지 않는다.
모든 변경은 신규 테이블 생성만으로 이루어지며 downgrade 시 역순 drop_table 로 완전히 복원된다.

추가 테이블:
- github_installations
- github_repos
- modernize_sessions
- codebase_analyses
- modernize_recommendations

Revision ID: 039
Revises: 038
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "039"
down_revision: str | None = "038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----------------------------------------------------------------------
    # 1) github_installations — GitHub App 설치 정보 (installation token 비저장)
    # ----------------------------------------------------------------------
    op.create_table(
        "github_installations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("installation_id", sa.BigInteger(), nullable=False),
        sa.Column("account_login", sa.String(length=200), nullable=False),
        sa.Column("account_type", sa.String(length=20), nullable=False),
        sa.Column("target_type", sa.String(length=20), nullable=True),
        sa.Column(
            "permissions",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "repository_selection",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'selected'"),
        ),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("installation_id"),
    )
    op.create_index(
        "ix_github_installations_user_id",
        "github_installations",
        ["user_id"],
    )
    op.create_index(
        "ix_github_installations_organization_id",
        "github_installations",
        ["organization_id"],
    )
    op.create_index(
        "ix_github_installations_installation_id",
        "github_installations",
        ["installation_id"],
    )

    # ----------------------------------------------------------------------
    # 2) github_repos — 설치된 repo 캐시 (24h TTL)
    # ----------------------------------------------------------------------
    op.create_table(
        "github_repos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("installation_id", sa.Uuid(), nullable=False),
        sa.Column("gh_repo_id", sa.BigInteger(), nullable=False),
        sa.Column("full_name", sa.String(length=300), nullable=False),
        sa.Column(
            "default_branch",
            sa.String(length=200),
            nullable=False,
            server_default=sa.text("'main'"),
        ),
        sa.Column(
            "private",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("language_primary", sa.String(length=50), nullable=True),
        sa.Column("pushed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["installation_id"],
            ["github_installations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "installation_id",
            "gh_repo_id",
            name="uq_github_repos_installation_gh_repo",
        ),
    )
    op.create_index(
        "ix_github_repos_installation_id",
        "github_repos",
        ["installation_id"],
    )

    # ----------------------------------------------------------------------
    # 3) modernize_sessions — Modernize 위저드 세션 + 분석 진행률
    # ----------------------------------------------------------------------
    op.create_table(
        "modernize_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("installation_id", sa.Uuid(), nullable=True),
        sa.Column("repo_full_name", sa.String(length=300), nullable=False),
        sa.Column(
            "repo_branch",
            sa.String(length=200),
            nullable=False,
            server_default=sa.text("'main'"),
        ),
        sa.Column("commit_sha", sa.String(length=64), nullable=True),
        sa.Column("scenario", sa.String(length=30), nullable=False),
        sa.Column("goals_text", sa.Text(), nullable=True),
        sa.Column("target_stack", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "progress_pct",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.Column(
            "extra",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["installation_id"],
            ["github_installations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_modernize_sessions_user_id",
        "modernize_sessions",
        ["user_id"],
    )
    op.create_index(
        "ix_modernize_sessions_organization_id",
        "modernize_sessions",
        ["organization_id"],
    )
    op.create_index(
        "ix_modernize_sessions_installation_id",
        "modernize_sessions",
        ["installation_id"],
    )

    # ----------------------------------------------------------------------
    # 4) codebase_analyses — 정적 분석 + LLM 요약 영속 (session_id 1:1)
    # ----------------------------------------------------------------------
    op.create_table(
        "codebase_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("loc_total", sa.Integer(), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=True),
        sa.Column(
            "lang_distribution",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "manifests",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("dep_graph", sa.JSON(), nullable=True),
        sa.Column(
            "outdated_packages",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column(
            "framework_signals",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "risk_flags",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("llm_summary_md", sa.Text(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["modernize_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(
        "ix_codebase_analyses_session_id",
        "codebase_analyses",
        ["session_id"],
    )

    # ----------------------------------------------------------------------
    # 5) modernize_recommendations — "이슈 1건 = 권장안 1건" 원자단위
    # ----------------------------------------------------------------------
    op.create_table(
        "modernize_recommendations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("target_path", sa.String(length=500), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("rationale_md", sa.Text(), nullable=True),
        sa.Column(
            "effort",
            sa.String(length=2),
            nullable=False,
            server_default=sa.text("'M'"),
        ),
        sa.Column(
            "risk",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'med'"),
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("50"),
        ),
        sa.Column("prompt_md", sa.Text(), nullable=True),
        sa.Column("linear_issue_id", sa.String(length=100), nullable=True),
        sa.Column("linear_identifier", sa.String(length=50), nullable=True),
        sa.Column(
            "selected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["modernize_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_modernize_recommendations_session_id",
        "modernize_recommendations",
        ["session_id"],
    )
    op.create_index(
        "ix_modernize_recommendations_session_idx",
        "modernize_recommendations",
        ["session_id", "idx"],
    )


def downgrade() -> None:
    # 신규 테이블 5종 역순 삭제 — 기존 테이블/컬럼/인덱스는 어느 것도 변경되지 않았으므로
    # downgrade 후 스키마는 038 시점과 완전히 동일하다 (R-7 회귀 안전).
    op.drop_index(
        "ix_modernize_recommendations_session_idx",
        table_name="modernize_recommendations",
    )
    op.drop_index(
        "ix_modernize_recommendations_session_id",
        table_name="modernize_recommendations",
    )
    op.drop_table("modernize_recommendations")

    op.drop_index(
        "ix_codebase_analyses_session_id",
        table_name="codebase_analyses",
    )
    op.drop_table("codebase_analyses")

    op.drop_index(
        "ix_modernize_sessions_installation_id",
        table_name="modernize_sessions",
    )
    op.drop_index(
        "ix_modernize_sessions_organization_id",
        table_name="modernize_sessions",
    )
    op.drop_index(
        "ix_modernize_sessions_user_id",
        table_name="modernize_sessions",
    )
    op.drop_table("modernize_sessions")

    op.drop_index(
        "ix_github_repos_installation_id",
        table_name="github_repos",
    )
    op.drop_table("github_repos")

    op.drop_index(
        "ix_github_installations_installation_id",
        table_name="github_installations",
    )
    op.drop_index(
        "ix_github_installations_organization_id",
        table_name="github_installations",
    )
    op.drop_index(
        "ix_github_installations_user_id",
        table_name="github_installations",
    )
    op.drop_table("github_installations")
