"""조직 멤버십 백필: users.organization_id → organization_memberships

Revision ID: 045
Revises: 044
Create Date: 2026-07-21 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "045"
down_revision: str | None = "044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # primary organization_id는 있으나 활성 멤버십이 없는 유저에 대해 멤버십을 백필한다.
    op.execute(
        """
        INSERT INTO organization_memberships
            (id, user_id, organization_id, org_role, invited_by, joined_at, is_active)
        SELECT gen_random_uuid(), u.id, u.organization_id, 'org_member', NULL, now(), true
        FROM users u
        WHERE u.organization_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM organization_memberships m
              WHERE m.user_id = u.id
                AND m.organization_id = u.organization_id
                AND m.is_active = true
          )
        """
    )


def downgrade() -> None:
    # 백필분은 정상 생성된 멤버십과 구분 불가 → no-op (삭제하지 않음)
    pass
