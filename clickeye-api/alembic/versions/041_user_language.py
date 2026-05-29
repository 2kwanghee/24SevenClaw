"""users 테이블에 language 컬럼 추가.

기존 사용자는 server_default "en"으로 자동 채워진다.
새 사용자는 "ko" 또는 "en" 중 하나를 지정할 수 있다.

Revision ID: 041
Revises: 040
Create Date: 2026-05-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "041"
down_revision: str | None = "040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "language",
            sa.String(8),
            nullable=False,
            server_default="en",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "language")
