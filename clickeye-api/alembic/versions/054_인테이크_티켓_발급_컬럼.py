"""인테이크 티켓 발급 컬럼 추가 (다프로젝트화 P6 — 티켓 전량 자동 발급)

intake_requests 에 티켓 발급 상태 3컬럼을 추가한다. 정제 스펙 → Linear 티켓 분해는
로컬 구독 배치(scripts/intake_issue.sh)가 수행하고 서버는 상태 조율·기록만 한다
(refine 배치와 동일한 실행 플레인 분리).

- tickets_status: none | issued — 발급 멱등성의 앵커(배치 재실행 시 중복 발급 방지)
- tickets: 발급 원장 JSON [{key, identifier, issue_id, title}]
- tickets_issued_at: 발급 시각

순수 additive — 기존 행은 전부 none 으로 시작하고, 발급 배치(opt-in)를 켜기 전에는
어떤 동작도 바뀌지 않는다.

Revision ID: 054
Revises: 053
Create Date: 2026-07-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "054"
down_revision: str | None = "053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "intake_requests",
        sa.Column(
            "tickets_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
    )
    op.add_column("intake_requests", sa.Column("tickets", sa.JSON(), nullable=True))
    op.add_column(
        "intake_requests",
        sa.Column("tickets_issued_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("intake_requests", "tickets_issued_at")
    op.drop_column("intake_requests", "tickets")
    op.drop_column("intake_requests", "tickets_status")
