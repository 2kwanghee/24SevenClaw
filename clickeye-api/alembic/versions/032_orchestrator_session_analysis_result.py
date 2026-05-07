"""오케스트레이터 세션에 분석 결과 컬럼 추가

Revision ID: 032
Revises: 031
Create Date: 2026-05-07
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orchestrator_sessions",
        sa.Column("analysis_result", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orchestrator_sessions", "analysis_result")
