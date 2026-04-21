"""Organization.business_type 100자로 확장 및 Project.project_type 30자·기본값 legacy 설정

Revision ID: 011
Revises: 010
Create Date: 2026-04-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # organizations.business_type: VARCHAR(20) → VARCHAR(100)
    op.alter_column(
        "organizations",
        "business_type",
        existing_type=sa.String(20),
        type_=sa.String(100),
        existing_nullable=True,
    )

    # projects.project_type: VARCHAR(50) → VARCHAR(30), DEFAULT 'legacy' 추가
    op.alter_column(
        "projects",
        "project_type",
        existing_type=sa.String(50),
        type_=sa.String(30),
        existing_nullable=True,
        server_default=sa.text("'legacy'"),
    )


def downgrade() -> None:
    # projects.project_type 복원
    op.alter_column(
        "projects",
        "project_type",
        existing_type=sa.String(30),
        type_=sa.String(50),
        existing_nullable=True,
        server_default=None,
    )

    # organizations.business_type 복원
    op.alter_column(
        "organizations",
        "business_type",
        existing_type=sa.String(100),
        type_=sa.String(20),
        existing_nullable=True,
    )
