"""활성 멤버십 부분 유니크 인덱스 추가 (CE-306 항목1)

동일 (user_id, organization_id) 에 대해 활성(is_active=true) 멤버십이 둘 이상
존재하면 `_authorize_target_org`/`add_org_member` 의 단건 조회가
MultipleResultsFound(500) 로 실패하고 조직-소유자 desync 가 재발한다. 부분
유니크 인덱스로 중복 활성 멤버십을 DB 레벨에서 근본 차단한다.

Revision ID: 047
Revises: 046
Create Date: 2026-07-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "047"
down_revision: str | None = "046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) dedupe: 유니크 인덱스 생성 전에 기존 중복 활성 행을 정리한다.
    #    동일 (user_id, organization_id) 에 is_active=true 인 행이 2건 이상이면
    #    가장 최근(joined_at DESC NULLS LAST, id) 1건만 남기고 나머지를
    #    is_active=false 로 비활성화한다. 멱등(재실행해도 남는 활성 1건만 유지).
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY user_id, organization_id
                        ORDER BY joined_at DESC NULLS LAST, id
                    ) AS rn
                FROM organization_memberships
                WHERE is_active IS TRUE
            )
            UPDATE organization_memberships AS m
            SET is_active = false
            FROM ranked
            WHERE m.id = ranked.id
              AND ranked.rn > 1
            """
        )
    )

    # 2) 활성 멤버십 부분 유니크 인덱스. is_active=true 인 행에 대해서만
    #    (user_id, organization_id) 유일성을 강제한다(비활성 이력 행은 무관).
    op.create_index(
        "uq_org_membership_active",
        "organization_memberships",
        ["user_id", "organization_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    # 인덱스만 제거한다. dedupe(비활성화) 는 데이터 정정이므로 되돌리지 않는다(no-op).
    op.drop_index("uq_org_membership_active", table_name="organization_memberships")
