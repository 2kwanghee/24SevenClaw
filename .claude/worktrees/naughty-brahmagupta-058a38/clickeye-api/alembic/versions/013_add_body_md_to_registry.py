"""Registry 모델(agents/skills/mcp_servers)에 body_md 컬럼 추가

Revision ID: 013
Revises: 012
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("body_md", sa.Text(), nullable=True))
    op.add_column("skills", sa.Column("body_md", sa.Text(), nullable=True))
    op.add_column("mcp_servers", sa.Column("body_md", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("mcp_servers", "body_md")
    op.drop_column("skills", "body_md")
    op.drop_column("agents", "body_md")
