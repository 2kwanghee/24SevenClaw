"""ai-critique 오퍼링 제거 (CE-334)

ai-critique 는 고객의 종량 API 키(OPENAI_API_KEY/GEMINI_API_KEY)로 GPT·Gemini 를
병렬 호출하는 유일한 오퍼링이었다. 구독형 전용 원칙에 어긋나고, 실행 스크립트
(call_gpt.sh/call_gemini.sh)가 딜리버리 팩에 동반되지 않아 애초에 작동하지 않았다.
카탈로그(skills.json/pipelines.json)와 PM composition 시드(data)에서 제거하는 것과
함께, 기존 DB 에 남아 있는 시드 행도 정리한다.

삭제 대상:
1) skills 테이블의 slug='ai-critique' 행 (023 이 시드, 034 가 body_md 갱신)
2) pm_compositions 테이블의 component_slug='ai-critique' 행
   (96e8e503b069 이 도메인별 PM 에 시드한 skill 컴포넌트)

pipelines 는 DB 테이블이 아니라 JSON 파일(pipelines.json)에서만 읽으므로 여기서
삭제할 DB 행이 없다 — 파이프라인 참조 제거는 카탈로그 JSON 편집으로 완결된다.

Revision ID: 058
Revises: 057
Create Date: 2026-07-30 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "058"
down_revision: str | None = "057"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    # PM composition 시드 행 삭제 (skill 타입의 ai-critique 컴포넌트)
    conn.execute(
        sa.text(
            "DELETE FROM pm_compositions "
            "WHERE component_type = 'skill' AND component_slug = 'ai-critique'"
        )
    )
    # 스킬 카탈로그 행 삭제
    conn.execute(sa.text("DELETE FROM skills WHERE slug = 'ai-critique'"))


def downgrade() -> None:
    # 복원 불가 — no-op.
    # ai-critique 행의 body_md/description/config 원본은 이 마이그레이션에서 보존하지
    # 않으므로 다운그레이드로 되살릴 수 없다. 필요 시 023/034/96e8e503b069 시드를
    # 재적용하는 별도 절차로 복구한다.
    pass
