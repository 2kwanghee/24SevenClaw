"""중앙 계약 관리 테이블 추가

Revision ID: 008
Revises: 007
Create Date: 2026-04-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "central_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("contract_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0.0"),
        sa.Column("content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allowed_overrides", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_central_contracts_slug", "central_contracts", ["slug"])
    op.create_index(
        "ix_central_contracts_contract_type", "central_contracts", ["contract_type"]
    )

    op.create_table(
        "customer_contract_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("central_contract_id", sa.Uuid(), nullable=False),
        sa.Column("override_content", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["central_contract_id"], ["central_contracts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_customer_contract_overrides_project_id",
        "customer_contract_overrides",
        ["project_id"],
    )
    op.create_index(
        "ix_customer_contract_overrides_central_contract_id",
        "customer_contract_overrides",
        ["central_contract_id"],
    )

    op.create_table(
        "contract_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=True),
        sa.Column("override_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("diff_snapshot", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["contract_id"], ["central_contracts.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["override_id"],
            ["customer_contract_overrides.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_contract_audit_logs_contract_id",
        "contract_audit_logs",
        ["contract_id"],
    )


def downgrade() -> None:
    op.drop_table("contract_audit_logs")
    op.drop_table("customer_contract_overrides")
    op.drop_table("central_contracts")
