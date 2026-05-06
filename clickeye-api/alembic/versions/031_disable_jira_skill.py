"""Jira 스킬 비활성화 (is_public=FALSE)

Revision ID: 031
Revises: 030
Create Date: 2026-05-06
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE skills SET is_public = FALSE WHERE slug = 'jira'")
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE skills SET is_public = TRUE WHERE slug = 'jira'")
    )
