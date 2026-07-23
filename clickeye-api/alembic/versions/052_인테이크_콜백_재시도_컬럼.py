"""인테이크 콜백 재시도 컬럼 추가 (CE-311)

accept/reject 상태 콜백의 at-least-once 전달을 위해 발송 상태·시도 횟수·
다음 재시도 시각·마지막 오류 4컬럼을 intake_requests 에 추가한다(무파괴).

Revision ID: 052
Revises: 051
Create Date: 2026-07-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "052"
down_revision: str | None = "051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # none | pending | sent | failed — 콜백 발송 상태(none = callback_url 없음).
    op.add_column(
        "intake_requests",
        sa.Column(
            "callback_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )
    # 발송 시도 횟수(성공 포함). 최대 6회(초기 1 + 재시도 5) 초과 실패 시 failed.
    op.add_column(
        "intake_requests",
        sa.Column(
            "callback_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    # 다음 재시도 예정 시각 — 재시도 워커(60s 폴링)가 due 건만 재발송.
    op.add_column(
        "intake_requests",
        sa.Column("callback_next_retry_at", sa.DateTime(timezone=True), nullable=True),
    )
    # 마지막 발송 실패 사유(관측용).
    op.add_column("intake_requests", sa.Column("callback_last_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("intake_requests", "callback_last_error")
    op.drop_column("intake_requests", "callback_next_retry_at")
    op.drop_column("intake_requests", "callback_attempts")
    op.drop_column("intake_requests", "callback_status")
