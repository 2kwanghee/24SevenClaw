"""LLM 사용량 원장 테이블 추가 (CE-299).

비침습성 원칙: 신규 테이블 `llm_usage_ledger` 하나만 추가한다. 기존 스키마는
건드리지 않으며 downgrade 로 완전히 복원된다. 게이트웨이는 feature flag
(feature_llm_gateway) 뒤에 배선되므로 이 테이블은 flag off 시 사용되지 않는다.

ENUM 타입은 028_add_roi_standards 패턴을 따른다: 컬럼은
`postgresql.ENUM(..., create_type=False)` 로 선언하고, 타입 생성/삭제는
upgrade 선두 / downgrade 말미의 명시적 CREATE TYPE / DROP TYPE 로 대칭 처리한다.
이로써 `downgrade -1` 후 `upgrade head` 재실행 시 DuplicateObject 가 나지 않는다.

Revision ID: 044
Revises: 043
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "044"
down_revision: str | None = "043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ENUM 타입 명시 생성(컬럼은 create_type=False 로 재사용).
    op.execute("CREATE TYPE llm_provider AS ENUM ('anthropic', 'openai')")
    op.execute(
        "CREATE TYPE llm_key_source AS ENUM ('subscription_seat', 'org_api_key')"
    )
    op.execute("CREATE TYPE llm_usage_status AS ENUM ('success', 'error')")

    op.create_table(
        "llm_usage_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.String(length=128), nullable=True),
        sa.Column(
            "provider",
            postgresql.ENUM(
                "anthropic", "openai", name="llm_provider", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "key_source",
            postgresql.ENUM(
                "subscription_seat",
                "org_api_key",
                name="llm_key_source",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("model", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost", sa.Numeric(precision=14, scale=6), nullable=True),
        sa.Column("request_kind", sa.String(length=64), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "success", "error", name="llm_usage_status", create_type=False
            ),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_llm_usage_ledger_created_at",
        "llm_usage_ledger",
        ["created_at"],
    )
    op.create_index(
        "ix_llm_usage_ledger_project_id",
        "llm_usage_ledger",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_llm_usage_ledger_project_id", table_name="llm_usage_ledger")
    op.drop_index("ix_llm_usage_ledger_created_at", table_name="llm_usage_ledger")
    op.drop_table("llm_usage_ledger")
    # 타입도 대칭 삭제 — 미삭제 시 재-upgrade 에서 DuplicateObject 발생.
    op.execute("DROP TYPE llm_usage_status")
    op.execute("DROP TYPE llm_key_source")
    op.execute("DROP TYPE llm_provider")
