"""PM 역할별 에이전트 스킬 composition 시드

Revision ID: 96e8e503b069
Revises: 875c7436fc10
Create Date: 2026-06-05 17:44:43.958970
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision: str = "96e8e503b069"
down_revision: str | None = "875c7436fc10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 본 마이그레이션이 시드한 composition 행 식별용 display_order 오프셋(다운그레이드 마커).
_SEED_ORDER_BASE = 100

# domain → 역할별 에이전트 slug (공개 카탈로그 내, harness 는 공통/필수)
_AGENTS: dict[str, list[str]] = {
    "fintech": ["harness", "backend", "security", "architect", "qa"],
    "ecommerce": ["harness", "backend", "frontend", "architect", "qa"],
    "ai": ["harness", "backend", "architect", "deep-thinker", "qa"],
    "healthcare": ["harness", "backend", "security", "frontend", "qa"],
    "marketplace": ["harness", "backend", "frontend", "architect", "qa"],
    "internal": ["harness", "backend", "frontend", "devops", "qa"],
    "saas": ["harness", "frontend", "devops", "pm-agent", "qa"],
    "realtime": ["harness", "backend", "architect", "devops", "qa"],
    "logistics": ["harness", "backend", "architect", "devops", "qa"],
    "mobile": ["harness", "frontend", "backend", "uiux", "qa"],
    "analytics": ["harness", "backend", "architect", "frontend", "qa"],
    "game": ["harness", "backend", "frontend", "architect", "qa"],
}
_DEFAULT_AGENTS = ["harness", "backend", "architect", "qa"]

# 공통 skill base + 도메인 가감 (공개 카탈로그 내)
_SKILLS_BASE = ["tdd-smart-coding", "ai-critique", "harness-gate", "verify-implementation"]
_SKILLS_EXTRA: dict[str, list[str]] = {
    "fintech": ["log-work"],
    "healthcare": ["log-work"],
    "internal": ["github", "linear"],
    "marketplace": ["github"],
    "ecommerce": ["github"],
    "saas": ["uiux", "fullstack"],
    "mobile": ["uiux"],
    "analytics": ["fullstack"],
}


def _catalog_names(conn: sa.Connection, table: str) -> dict[str, str]:
    """공개(is_public) slug → name 맵. 카탈로그에 없는 slug 는 삽입하지 않기 위한 필터 겸용."""
    rows = conn.execute(
        sa.text(f"SELECT slug, name FROM {table} WHERE is_public = true")  # noqa: S608 (고정 테이블명)
    ).all()
    return {r[0]: r[1] for r in rows}


def upgrade() -> None:
    conn = op.get_bind()
    agent_names = _catalog_names(conn, "agents")
    skill_names = _catalog_names(conn, "skills")

    pms = conn.execute(sa.text("SELECT id, domain FROM pm_profiles")).all()
    for pm_id, domain in pms:
        existing = {
            (r[0], r[1])
            for r in conn.execute(
                sa.text(
                    "SELECT component_type, component_slug FROM pm_compositions WHERE pm_id = :p"
                ),
                {"p": pm_id},
            )
        }
        agents = _AGENTS.get(domain or "", _DEFAULT_AGENTS)
        skills = _SKILLS_BASE + _SKILLS_EXTRA.get(domain or "", [])
        plan: list[tuple[str, str, bool, dict[str, str]]] = [
            *[("agent", s, s == "harness", agent_names) for s in agents],
            *[("skill", s, False, skill_names) for s in skills],
        ]

        order = {"agent": 0, "skill": 0}
        for ctype, slug, required, names in plan:
            if (ctype, slug) in existing:
                continue
            name = names.get(slug)
            if name is None:  # 공개 카탈로그에 없는 slug 는 안전하게 스킵
                continue
            o = order[ctype]
            order[ctype] = o + 1
            conn.execute(
                sa.text(
                    """
                    INSERT INTO pm_compositions
                        (id, pm_id, component_type, component_slug, component_name,
                         config, display_order, is_required)
                    VALUES
                        (:id, :pm, :t, :s, :n, '{}', :o, :req)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "pm": pm_id,
                    "t": ctype,
                    "s": slug,
                    "n": name,
                    "o": _SEED_ORDER_BASE + o,
                    "req": required,
                },
            )


def downgrade() -> None:
    # 본 시드 행만 식별(display_order >= 100 마커). 기존 큐레이션(0~99)은 보존.
    op.get_bind().execute(
        sa.text(
            "DELETE FROM pm_compositions "
            "WHERE display_order >= :base AND component_type IN ('agent', 'skill')"
        ),
        {"base": _SEED_ORDER_BASE},
    )
