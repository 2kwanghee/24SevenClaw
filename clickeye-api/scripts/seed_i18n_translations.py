"""카탈로그 핵심 항목 영문 번역 시딩 스크립트 (i18n Phase 3).

agents/skills에 name_en, description_en, body_md_en 을 업데이트한다.
pm_profiles에 name_en, title_en, description_en 을 업데이트한다.
멱등 — 재실행 시 동일 값으로 덮어쓰므로 안전하다.

Usage:
    cd clickeye-api
    uv run python -m scripts.seed_i18n_translations
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.pm_profile import PMProfile
from app.models.registry import Agent, Skill

logger = logging.getLogger(__name__)

# ─── Agent 번역 ────────────────────────────────────────────────────────────────
AGENT_TRANSLATIONS: list[dict] = [
    {
        "slug": "backend",
        "name_en": "Backend Engineer",
        "description_en": "FastAPI/Django backend specialist. APIs, DB modeling, performance.",
        "body_md_en": None,
    },
    {
        "slug": "fullstack",
        "name_en": "Full-Stack Engineer",
        "description_en": "Full-stack specialist covering frontend and backend. Next.js + FastAPI.",
        "body_md_en": None,
    },
    {
        "slug": "ai-critique",
        "name_en": "AI Code Reviewer",
        "description_en": "AI-powered code review. Detects bugs and anti-patterns.",
        "body_md_en": None,
    },
]

# ─── Skill 번역 ────────────────────────────────────────────────────────────────
SKILL_TRANSLATIONS: list[dict] = [
    {
        "slug": "harness",
        "name_en": "Harness Engineering",
        "description_en": "5-phase AI workflow. Prevents hallucinations and errors upfront.",
        "body_md_en": None,
    },
    {
        "slug": "tdd-smart-coding",
        "name_en": "TDD Smart Coding",
        "description_en": "TDD: write tests first, then implement. Prevents regressions.",
        "body_md_en": None,
    },
    {
        "slug": "github",
        "name_en": "GitHub Integration",
        "description_en": "GitHub automation. PR creation, branch management, commit conventions.",
        "body_md_en": None,
    },
    {
        "slug": "linear",
        "name_en": "Linear Integration",
        "description_en": "Linear issue integration. Auto-updates issue status on task completion.",
        "body_md_en": None,
    },
    {
        "slug": "postgres",
        "name_en": "PostgreSQL",
        "description_en": "PostgreSQL integration. Migration management and query optimization.",
        "body_md_en": None,
    },
    {
        "slug": "harness-gate",
        "name_en": "Harness Gate",
        "description_en": "Plan Gate hook. Blocks code changes without an approved plan file.",
        "body_md_en": None,
    },
    {
        "slug": "commit-session",
        "name_en": "Commit Session",
        "description_en": "Auto-commit after each task. Maintains granular git history.",
        "body_md_en": None,
    },
    {
        "slug": "ralph-loop",
        "name_en": "Ralph Loop",
        "description_en": "Autonomous agent. Processes fix_plan.md items and auto-commits.",
        "body_md_en": None,
    },
]

# ─── PM Profile 번역 ──────────────────────────────────────────────────────────
PM_TRANSLATIONS: list[dict] = [
    {
        "slug": "atlas",
        "name_en": "Atlas",
        "title_en": "Backend Architecture PM",
        "description_en": "Scalable backend specialist. Excels at API design and data modeling.",
    },
    {
        "slug": "nova",
        "name_en": "Nova",
        "title_en": "Full-Stack PM",
        "description_en": "Full-stack PM. Bridges frontend and backend for complete solutions.",
    },
    {
        "slug": "bridge",
        "name_en": "Bridge",
        "title_en": "API Integration PM",
        "description_en": "Third-party API integration expert. Reliability and interoperability.",
    },
    {
        "slug": "forge",
        "name_en": "Forge",
        "title_en": "Data Engineering PM",
        "description_en": "Data pipeline and analytics leader. ETL and large-scale data expertise.",
    },
]


async def seed_agent_translations(db: AsyncSession) -> int:
    updated = 0
    for item in AGENT_TRANSLATIONS:
        slug = item["slug"]
        stmt = select(Agent).where(Agent.slug == slug)
        result = await db.execute(stmt)
        agent = result.scalar_one_or_none()
        if agent is None:
            logger.warning("Agent not found: %s", slug)
            continue
        values: dict = {}
        if item.get("name_en"):
            values["name_en"] = item["name_en"]
        if item.get("description_en"):
            values["description_en"] = item["description_en"]
        if item.get("body_md_en"):
            values["body_md_en"] = item["body_md_en"]
        if values:
            await db.execute(update(Agent).where(Agent.slug == slug).values(**values))
            updated += 1
    return updated


async def seed_skill_translations(db: AsyncSession) -> int:
    updated = 0
    for item in SKILL_TRANSLATIONS:
        slug = item["slug"]
        stmt = select(Skill).where(Skill.slug == slug)
        result = await db.execute(stmt)
        skill = result.scalar_one_or_none()
        if skill is None:
            logger.warning("Skill not found: %s", slug)
            continue
        values: dict = {}
        if item.get("name_en"):
            values["name_en"] = item["name_en"]
        if item.get("description_en"):
            values["description_en"] = item["description_en"]
        if item.get("body_md_en"):
            values["body_md_en"] = item["body_md_en"]
        if values:
            await db.execute(update(Skill).where(Skill.slug == slug).values(**values))
            updated += 1
    return updated


async def seed_pm_translations(db: AsyncSession) -> int:
    updated = 0
    for item in PM_TRANSLATIONS:
        slug = item["slug"]
        stmt = select(PMProfile).where(PMProfile.slug == slug)
        result = await db.execute(stmt)
        pm = result.scalar_one_or_none()
        if pm is None:
            logger.warning("PMProfile not found: %s", slug)
            continue
        values: dict = {}
        if item.get("name_en"):
            values["name_en"] = item["name_en"]
        if item.get("title_en"):
            values["title_en"] = item["title_en"]
        if item.get("description_en"):
            values["description_en"] = item["description_en"]
        if values:
            await db.execute(update(PMProfile).where(PMProfile.slug == slug).values(**values))
            updated += 1
    return updated


async def seed_all(db: AsyncSession) -> dict[str, int]:
    agents_updated = await seed_agent_translations(db)
    skills_updated = await seed_skill_translations(db)
    pms_updated = await seed_pm_translations(db)
    await db.commit()
    return {
        "agents": agents_updated,
        "skills": skills_updated,
        "pm_profiles": pms_updated,
    }


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    async with async_session() as db:
        results = await seed_all(db)
    logger.info("i18n 시드 완료: %s", results)


if __name__ == "__main__":
    asyncio.run(main())
