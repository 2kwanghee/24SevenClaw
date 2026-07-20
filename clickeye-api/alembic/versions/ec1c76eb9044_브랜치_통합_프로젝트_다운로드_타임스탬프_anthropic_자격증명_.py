"""브랜치 통합 — 프로젝트 다운로드 타임스탬프 + Anthropic 자격증명 테이블

Revision ID: ec1c76eb9044
Revises: 033, cebdfdc9be4c
Create Date: 2026-05-08 16:21:47.716617
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic
revision: str = "ec1c76eb9044"
down_revision: str | None = ("033", "cebdfdc9be4c")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
