"""i18n 및 organizations 브랜치 통합

Revision ID: 875c7436fc10
Revises: 041, 9f0519f73fcf
Create Date: 2026-05-29 09:33:25.437336
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision: str = '875c7436fc10'
down_revision: Union[str, None] = ('041', '9f0519f73fcf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
