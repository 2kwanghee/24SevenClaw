"""컨트롤 타워 — 고객사/프로젝트 관리자 기능

organizations: org_type, account_manager_id, customer_status 추가
projects: organization_id FK 추가 (고객사↔프로젝트 직접 연결)

Revision ID: 026
Revises: 025
Create Date: 2026-04-25 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # organizations 테이블에 컨트롤 타워용 컬럼 추가
    op.add_column(
        "organizations",
        sa.Column(
            "org_type",
            sa.String(20),
            nullable=False,
            server_default="customer",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "account_manager_id",
            sa.Uuid(),
            nullable=True,
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "customer_status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
    )
    op.create_foreign_key(
        "fk_organizations_account_manager",
        "organizations",
        "users",
        ["account_manager_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # projects 테이블에 organization_id FK 추가
    op.add_column(
        "projects",
        sa.Column("organization_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_projects_organization_id",
        "projects",
        ["organization_id"],
    )
    op.create_foreign_key(
        "fk_projects_organization",
        "projects",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 백필: 프로젝트 소유자의 organization_id를 프로젝트에 복사
    op.execute(
        """
        UPDATE projects p
        SET organization_id = u.organization_id
        FROM users u
        WHERE u.id = p.owner_id
          AND u.organization_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_projects_organization", "projects", type_="foreignkey")
    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_column("projects", "organization_id")

    op.drop_constraint(
        "fk_organizations_account_manager", "organizations", type_="foreignkey"
    )
    op.drop_column("organizations", "customer_status")
    op.drop_column("organizations", "account_manager_id")
    op.drop_column("organizations", "org_type")
