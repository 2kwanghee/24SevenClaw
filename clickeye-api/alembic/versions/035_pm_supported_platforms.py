"""pm_profiles에 supported_platforms 컬럼 추가 및 platform agent 데이터 이전.

pm_compositions에서 component_type='agent'이고 component_slug이
플랫폼 슬러그(claude-code, gemini-cli, cursor, codex)인 행을
pm_profiles.supported_platforms 컬럼으로 이전하고 해당 composition 행을 삭제한다.

Revision ID: 035
Revises: 034
Create Date: 2026-05-14
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "035"
down_revision: str | None = "034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PLATFORM_SLUGS = frozenset(["claude-code", "gemini-cli", "cursor", "codex"])


def upgrade() -> None:
    # 1. supported_platforms 컬럼 추가
    op.add_column(
        "pm_profiles",
        sa.Column(
            "supported_platforms",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )

    # 2. 기존 pm_compositions에서 platform 슬러그를 supported_platforms로 이전
    conn = op.get_bind()

    # PM별로 platform agent compositions를 모아 이전
    rows = conn.execute(
        sa.text(
            """
            SELECT pc.pm_id, array_agg(pc.component_slug ORDER BY pc.display_order) AS slugs
            FROM pm_compositions pc
            WHERE pc.component_type = 'agent'
              AND pc.component_slug IN :slugs
            GROUP BY pc.pm_id
            """
        ).bindparams(sa.bindparam("slugs", expanding=True)),
        {"slugs": list(_PLATFORM_SLUGS)},
    ).fetchall()

    for row in rows:
        pm_id, slugs = row
        existing = conn.execute(
            sa.text("SELECT supported_platforms FROM pm_profiles WHERE id = :pm_id"),
            {"pm_id": pm_id},
        ).scalar()
        existing_list: list[str] = existing if isinstance(existing, list) else []
        merged = list(dict.fromkeys(existing_list + list(slugs)))
        conn.execute(
            sa.text(
                "UPDATE pm_profiles SET supported_platforms = cast(:platforms as json) WHERE id = :pm_id"
            ),
            {"platforms": json.dumps(merged), "pm_id": pm_id},
        )

    # 3. 이전된 composition 행 삭제
    conn.execute(
        sa.text(
            """
            DELETE FROM pm_compositions
            WHERE component_type = 'agent'
              AND component_slug IN :slugs
            """
        ).bindparams(sa.bindparam("slugs", expanding=True)),
        {"slugs": list(_PLATFORM_SLUGS)},
    )


def downgrade() -> None:
    # supported_platforms 데이터를 pm_compositions으로 복원하는 것은 불가역적이므로
    # 컬럼만 제거하며, 삭제된 composition 행은 복원하지 않는다.
    op.drop_column("pm_profiles", "supported_platforms")
