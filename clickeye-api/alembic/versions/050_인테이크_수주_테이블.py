"""인테이크 수주 테이블 추가 (Chunk A1)

외부 서비스가 요구사항 정의서를 접수하는 게이트형 인테이크 수주 API 용
intake_service_keys / intake_requests 두 테이블을 생성한다.

Revision ID: 050
Revises: 049
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "050"
down_revision: str | None = "049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 서비스별 인테이크 API 키 (sha256 해시만 저장).
    op.create_table(
        "intake_service_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_intake_service_keys_key_hash", "intake_service_keys", ["key_hash"], unique=True
    )
    op.create_index(
        "ix_intake_service_keys_organization_id", "intake_service_keys", ["organization_id"]
    )

    # 인테이크 수주 요청 (pending_review → accepted/rejected).
    op.create_table(
        "intake_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_key_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=True),
        sa.Column("input_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("target", sa.JSON(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("callback_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending_review'"),
        ),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["service_key_id"], ["intake_service_keys.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("service_key_id", "idempotency_key", name="uq_intake_idempotency"),
    )
    op.create_index("ix_intake_requests_service_key_id", "intake_requests", ["service_key_id"])
    op.create_index("ix_intake_requests_status", "intake_requests", ["status"])
    op.create_index("ix_intake_requests_project_id", "intake_requests", ["project_id"])


def downgrade() -> None:
    op.drop_table("intake_requests")
    op.drop_table("intake_service_keys")
