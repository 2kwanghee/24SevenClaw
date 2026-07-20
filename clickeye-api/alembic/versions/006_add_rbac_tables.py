"""RBAC 테이블 추가: organization_memberships, role_audit_logs + users.system_role

Revision ID: 006
Revises: 7ed6d815b022
Create Date: 2026-04-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006"
down_revision: str | None = "7ed6d815b022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users 테이블에 system_role 컬럼 추가
    op.add_column(
        "users",
        sa.Column(
            "system_role",
            sa.String(20),
            server_default="member",
            nullable=False,
        ),
    )

    # organization_memberships 테이블 생성
    op.create_table(
        "organization_memberships",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(), nullable=False),
        sa.Column("organization_id", postgresql.UUID(), nullable=False),
        sa.Column(
            "org_role",
            sa.String(20),
            server_default="org_member",
            nullable=False,
        ),
        sa.Column("invited_by", postgresql.UUID(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_organization_memberships_user_id",
        "organization_memberships",
        ["user_id"],
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )

    # role_audit_logs 테이블 생성
    op.create_table(
        "role_audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("actor_id", postgresql.UUID(), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("old_value", sa.String(100), nullable=True),
        sa.Column("new_value", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("role_audit_logs")
    op.drop_index("ix_organization_memberships_organization_id")
    op.drop_index("ix_organization_memberships_user_id")
    op.drop_table("organization_memberships")
    op.drop_column("users", "system_role")
