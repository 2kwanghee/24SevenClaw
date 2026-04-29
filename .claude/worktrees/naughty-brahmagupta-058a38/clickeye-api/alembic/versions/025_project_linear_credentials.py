"""프로젝트별 Linear 자격증명 테이블 추가

프로젝트 삭제 시 CASCADE DELETE로 자동 정리됨.
유저 단위 UserLinearCredentials는 전역 설정용으로 유지.

Revision ID: 025
Revises: 024
Create Date: 2026-04-25 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_linear_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("team_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )


def downgrade() -> None:
    op.drop_table("project_linear_credentials")
