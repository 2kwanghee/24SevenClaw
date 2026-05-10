"""organizations 테이블에 features JSONB 컬럼 추가

Revision ID: 9f0519f73fcf
Revises: 473eddce9fcb
Create Date: 2026-05-10 11:56:34.167317
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision: str = '9f0519f73fcf'
down_revision: Union[str, None] = '473eddce9fcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'organizations',
        sa.Column('features', sa.JSON(), server_default='{}', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('organizations', 'features')
