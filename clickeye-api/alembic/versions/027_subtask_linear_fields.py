"""subtasks 테이블에 Linear 이슈 추적 필드 추가

linear_identifier: 이슈 식별자 (예: 24S-5)
linear_issue_id: Linear 내부 UUID
linear_state: 현재 Linear 상태명 (Wait, Queued, In Progress, Done)

Revision ID: 027
Revises: 026
Create Date: 2026-04-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "027"
down_revision: str | None = "026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("subtasks", sa.Column("linear_identifier", sa.String(50), nullable=True))
    op.add_column("subtasks", sa.Column("linear_issue_id", sa.String(100), nullable=True))
    op.add_column("subtasks", sa.Column("linear_state", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("subtasks", "linear_state")
    op.drop_column("subtasks", "linear_issue_id")
    op.drop_column("subtasks", "linear_identifier")
