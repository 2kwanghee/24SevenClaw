"""딜리버리 이벤트 테이블 추가 (다프로젝트화 P9 — 기록면 1급화)

무인 체인의 전이 이력(수신→정제→수락→발급→검증→콜백)을 append-only 로 기록하는
delivery_events 테이블을 생성한다. 인테이크 상태 컬럼은 스냅샷만 담으므로, 사후 감사·
정지 원인 추적·대시보드 타임라인은 이 테이블이 원천이다(D-8·D-9 — 실패 전이도 기록).

순수 additive — 기존 테이블 무변경. 이벤트 기록 훅(intake_service)이 붙기 전에는
어떤 동작도 바뀌지 않는다.

Revision ID: 055
Revises: 054
Create Date: 2026-07-28 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "055"
down_revision: str | None = "054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("intake_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        # machine | human | system
        sa.Column(
            "actor_type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'system'"),
        ),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["intake_id"], ["intake_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
    )
    # 타임라인 조회(intake_id, created_at)와 집계(event_type) 인덱스.
    op.create_index("ix_delivery_events_intake_id", "delivery_events", ["intake_id"])
    op.create_index("ix_delivery_events_project_id", "delivery_events", ["project_id"])
    op.create_index("ix_delivery_events_event_type", "delivery_events", ["event_type"])
    op.create_index("ix_delivery_events_created_at", "delivery_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_delivery_events_created_at", table_name="delivery_events")
    op.drop_index("ix_delivery_events_event_type", table_name="delivery_events")
    op.drop_index("ix_delivery_events_project_id", table_name="delivery_events")
    op.drop_index("ix_delivery_events_intake_id", table_name="delivery_events")
    op.drop_table("delivery_events")
