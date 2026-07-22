"""폐기된 Modernize 백엔드 테이블 6종 드롭 (딜리버리 전환 후속 정리)

Modernize(기존 코드 현대화 파이프라인, MVP-2-A) 기능이 폐기됨에 따라 전용 테이블을
모두 제거한다. FK 의존 역순으로 드롭한다:

  modernize_phase_artifacts / modernize_recommendations / codebase_analyses
    → modernize_sessions → github_repos → github_installations

폐기 기능이므로 downgrade 는 재생성하지 않는다(no-op). prototype/pm/projects 등
생존 테이블·컬럼은 일절 건드리지 않는다.

Revision ID: 048
Revises: 047
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "048"
down_revision: str | None = "047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # FK 역순 — modernize_sessions 를 참조하는 자식 테이블부터 드롭.
    # (drop_table 은 해당 테이블의 인덱스/FK 제약을 함께 제거한다.)
    op.drop_table("modernize_phase_artifacts")
    op.drop_table("modernize_recommendations")
    op.drop_table("codebase_analyses")
    # modernize_sessions 는 github_installations 를 참조하므로 그보다 먼저 드롭.
    op.drop_table("modernize_sessions")
    op.drop_table("github_repos")
    op.drop_table("github_installations")


def downgrade() -> None:
    # 폐기된 기능이므로 스키마 재생성은 하지 않는다(no-op).
    pass
