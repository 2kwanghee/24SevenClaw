"""구독 시트 컬럼 추가 (다프로젝트화 P4 — 등록형 시트·계정별 모니터링 축)

두 개의 additive 변경만 담는다.

1) user_anthropic_credentials.seat_status — 구독 시트(credential_type='oauth_token')의
   상태(active|exhausted|blocked). 기존 api_key 행은 server_default 'active' 로 채워지며
   의미를 갖지 않는다.
2) llm_usage_ledger.seat_id — 어느 시트가 토큰을 소비했는지의 1급 축(D-8).
   시트 삭제 시 원장 행은 보존하고 축만 끊는다(ondelete SET NULL).

순수 additive — 기존 자격증명/원장 플로우는 이 마이그레이션만으로 동작이 바뀌지 않는다.

Revision ID: 056
Revises: 055
Create Date: 2026-07-29 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "056"
down_revision: str | None = "055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # active | exhausted | blocked — oauth_token 행에서만 의미가 있다.
    op.add_column(
        "user_anthropic_credentials",
        sa.Column(
            "seat_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
    )
    op.add_column("llm_usage_ledger", sa.Column("seat_id", sa.Uuid(), nullable=True))
    op.create_index("ix_llm_usage_ledger_seat_id", "llm_usage_ledger", ["seat_id"])
    op.create_foreign_key(
        "fk_llm_usage_ledger_seat_id",
        "llm_usage_ledger",
        "user_anthropic_credentials",
        ["seat_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_llm_usage_ledger_seat_id", "llm_usage_ledger", type_="foreignkey")
    op.drop_index("ix_llm_usage_ledger_seat_id", table_name="llm_usage_ledger")
    op.drop_column("llm_usage_ledger", "seat_id")
    op.drop_column("user_anthropic_credentials", "seat_status")
