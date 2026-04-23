"""API 키 가이드 body_md 시드 — Telegram / Slack / GitHub / Jira

023에서 body_md_rel="" 으로 비어있던 4개 스킬에 가이드 Markdown을 채운다.
ON CONFLICT 없이 UPDATE만 수행 (slug 기준, body_md가 비어있는 경우만).
멱등성 보장: 이미 body_md가 있으면 건드리지 않는다.

Revision ID: 024
Revises: 023
Create Date: 2026-04-23 00:00:00.000000
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_GUIDES_DIR = Path(__file__).parent.parent.parent / "app" / "data" / "api-key-guides"

_SLUG_TO_FILE: dict[str, str] = {
    "telegram": "telegram.md",
    "slack": "slack.md",
    "github": "github.md",
    "jira": "jira.md",
}


def _read_guide(filename: str) -> str:
    path = _GUIDES_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def upgrade() -> None:
    conn = op.get_bind()
    for slug, filename in _SLUG_TO_FILE.items():
        body_md = _read_guide(filename)
        if not body_md:
            continue
        conn.execute(
            sa.text(
                "UPDATE skills SET body_md = :body_md "
                "WHERE slug = :slug AND (body_md IS NULL OR body_md = '')"
            ),
            {"body_md": body_md, "slug": slug},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for slug in _SLUG_TO_FILE:
        conn.execute(
            sa.text("UPDATE skills SET body_md = '' WHERE slug = :slug"),
            {"slug": slug},
        )
