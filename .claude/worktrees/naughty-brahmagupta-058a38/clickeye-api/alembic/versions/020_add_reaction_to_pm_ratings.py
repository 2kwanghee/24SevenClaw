"""pm_ratings 테이블에 reaction 컬럼 추가

Revision ID: 020
Revises: 019
Create Date: 2026-04-23 00:00:00.000000
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "pm_ratings",
        sa.Column("reaction", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pm_ratings", "reaction")
