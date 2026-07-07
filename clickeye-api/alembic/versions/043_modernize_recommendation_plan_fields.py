"""Modernize plan phase — 권장안에 depends_on/wave/assigned_agent 컬럼 추가.

비침습성 원칙: 기존 컬럼/인덱스는 건드리지 않는다. `modernize_recommendations`에
nullable=False + server_default 컬럼 3개를 추가할 뿐이며, downgrade 로 완전히 복원된다.

Revision ID: 043
Revises: 042
Create Date: 2026-07-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "043"
down_revision: str | None = "042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "modernize_recommendations",
        sa.Column(
            "depends_on",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )
    op.add_column(
        "modernize_recommendations",
        sa.Column(
            "wave",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "modernize_recommendations",
        sa.Column("assigned_agent", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("modernize_recommendations", "assigned_agent")
    op.drop_column("modernize_recommendations", "wave")
    op.drop_column("modernize_recommendations", "depends_on")
