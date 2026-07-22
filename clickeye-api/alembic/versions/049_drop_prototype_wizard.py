"""폐기된 위저드 2b(prototype-session) 스키마 제거

위저드 2b(prototype-session/prototype) 기능이 폐기되어 생성 경로가 죽었으므로
관련 vestigial 컬럼과 테이블을 정리한다. PM 평가(pm_ratings)와 프로젝트(projects)는
생존하되 session 참조만 제거된다.

  - pm_ratings.session_id 컬럼(+FK/인덱스) 드롭 — 평가 키는 pm_id + user_id
  - projects.prototype_session_id 컬럼(+FK/인덱스) 드롭
  - projects.wizard_data 컬럼 드롭
  - prototype_sessions ↔ prototypes 순환 FK 테이블 2종 DROP (CASCADE)

drop_column 은 PostgreSQL 에서 해당 컬럼에 종속된 FK/인덱스를 함께 제거한다.
prototype_sessions/prototypes 는 상호 참조(use_alter)하므로 CASCADE 로 드롭한다.
폐기 기능이므로 downgrade 는 재생성하지 않는다(no-op).

Revision ID: 049
Revises: 048
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "049"
down_revision: str | None = "048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) 생존 테이블에서 vestigial 컬럼 제거 (FK/인덱스 동반 제거).
    op.drop_column("pm_ratings", "session_id")
    op.drop_column("projects", "prototype_session_id")
    op.drop_column("projects", "wizard_data")

    # 2) 폐기된 위저드 2b 테이블 드롭 — 순환 FK 는 CASCADE 로 해소.
    op.execute("DROP TABLE IF EXISTS prototypes CASCADE")
    op.execute("DROP TABLE IF EXISTS prototype_sessions CASCADE")


def downgrade() -> None:
    # 폐기된 기능이므로 스키마 재생성은 하지 않는다(no-op).
    pass
