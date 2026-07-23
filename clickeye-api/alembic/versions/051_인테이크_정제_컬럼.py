"""인테이크 정제 컬럼 추가 (Chunk A3-full)

로컬 metaprompt 정제 배치(scripts/intake_refine.sh) 결과를 저장하는
refined_text / refine_status 두 컬럼을 intake_requests 에 추가한다(무파괴).

Revision ID: 051
Revises: 050
Create Date: 2026-07-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "051"
down_revision: str | None = "050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 정제된 구현 스펙 본문 (없으면 accept 시 normalized_text 폴백 — 기존 동작 유지).
    op.add_column("intake_requests", sa.Column("refined_text", sa.Text(), nullable=True))
    # pending | refined | skipped — 정제 배치 처리 상태.
    op.add_column(
        "intake_requests",
        sa.Column(
            "refine_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("intake_requests", "refine_status")
    op.drop_column("intake_requests", "refined_text")
