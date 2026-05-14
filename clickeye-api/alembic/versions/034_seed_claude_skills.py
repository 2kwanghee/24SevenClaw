"""`.claude/skills/` 공개 스킬 5개의 body_md를 갱신한다

migration 023이 이미 name/category/is_public을 올바르게 설정했으므로
이 migration은 body_md/description/output_file/version만 갱신한다.
category는 023의 taxonomy(quality/pipeline)를 유지한다.

Revision ID: 034
Revises: 033
Create Date: 2026-05-14
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "034"
down_revision: str | tuple[str, ...] | None = "033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NOW = datetime(2026, 5, 14, tzinfo=UTC)

# PM compositions 에 배정할 핵심 공개 스킬 슬러그
_TARGET_SLUGS: frozenset[str] = frozenset(
    ["fullstack", "uiux", "tdd-smart-coding", "ai-critique", "verify-implementation"]
)

_CATALOG_JSON = (
    Path(__file__).resolve().parent.parent.parent / "app" / "data" / "catalog" / "skills.json"
)


def _load_target_skills() -> list[dict[str, object]]:
    with _CATALOG_JSON.open(encoding="utf-8") as f:
        catalog: list[dict[str, object]] = json.load(f)
    return [entry for entry in catalog if entry["slug"] in _TARGET_SLUGS]


def upgrade() -> None:
    conn = op.get_bind()
    skills = _load_target_skills()

    for s in skills:
        conn.execute(
            sa.text(
                """
                INSERT INTO skills (
                    id, name, slug, description, body_md,
                    version, category, is_public, required,
                    output_file, dependencies, hook_events, env_vars,
                    config_schema, created_at, updated_at
                )
                VALUES (
                    :id, :name, :slug, :description, :body_md,
                    '1.0.0', 'workflow', TRUE, FALSE,
                    :output_file, '[]', '[]', '[]',
                    '{}', :now, :now
                )
                ON CONFLICT (slug) DO UPDATE
                    SET description = EXCLUDED.description,
                        body_md     = EXCLUDED.body_md,
                        output_file = EXCLUDED.output_file,
                        version     = EXCLUDED.version,
                        updated_at  = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": s["name"],
                "slug": s["slug"],
                "description": s.get("description") or "",
                "body_md": s.get("body_md") or "",
                "output_file": s["output_file"],
                "now": _NOW,
            },
        )


def downgrade() -> None:
    # body_md만 NULL로 복원 (023이 설정한 category/name은 건드리지 않는다)
    conn = op.get_bind()
    for slug in _TARGET_SLUGS:
        conn.execute(
            sa.text(
                "UPDATE skills SET body_md = NULL, updated_at = :now WHERE slug = :slug"
            ),
            {"slug": slug, "now": _NOW},
        )
