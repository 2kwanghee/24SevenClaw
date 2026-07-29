"""원장 세션 아이디 컬럼 + 멱등 인덱스 추가 (CE-328 — 로컬 배치 사용량 인제스트)

두 개의 additive 변경만 담는다.

1) llm_usage_ledger.session_id — 로컬 배치(claude -p) result 이벤트의 session_id.
   로컬 유입분(request_kind='local_batch_%')의 멱등 인제스트 키. in-API 게이트웨이
   호출은 session 개념이 없어 NULL 로 남는다.
2) 부분 유니크 인덱스 (session_id, model) WHERE session_id IS NOT NULL —
   동일 세션의 동일 모델 재전송(파이프라인 재실행/재시도)을 DB 레벨에서 차단하는
   백스톱. session_id 가 NULL 인 기존 in-API 행에는 유일성을 강제하지 않는다.

순수 additive — 기존 원장 플로우는 이 마이그레이션만으로 동작이 바뀌지 않는다.

Revision ID: 057
Revises: 056
Create Date: 2026-07-29 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "057"
down_revision: str | None = "056"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "llm_usage_ledger",
        sa.Column("session_id", sa.String(length=64), nullable=True),
    )
    # (session_id, model) 유일성은 session_id 가 존재하는 행에만 강제한다.
    op.create_index(
        "uq_llm_usage_ledger_session_model",
        "llm_usage_ledger",
        ["session_id", "model"],
        unique=True,
        postgresql_where=sa.text("session_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_llm_usage_ledger_session_model", table_name="llm_usage_ledger")
    op.drop_column("llm_usage_ledger", "session_id")
