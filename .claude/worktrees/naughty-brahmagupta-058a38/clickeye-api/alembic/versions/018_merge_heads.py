"""브랜치 통합 (017 + 7ed6d815b022 + c255febcea16)

Revision ID: 018
Revises: 017, 7ed6d815b022, c255febcea16
Create Date: 2026-04-22 00:00:00.000000
"""
from typing import Sequence, Union

revision: str = '018'
down_revision: Union[str, tuple[str, ...], None] = ('017', '7ed6d815b022', 'c255febcea16')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
