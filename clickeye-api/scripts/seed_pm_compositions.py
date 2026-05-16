"""20개 PM의 구성 컴포넌트(에이전트/스킬/MCP/Hook) 일괄 재구성 + bio_long 동기화.

각 PM의 도메인에 적합한 레지스트리 항목을 매핑 테이블 기반으로 등록한다.
실행 시 기존 composition은 전부 삭제되고 새 매핑으로 재등록된다 (멱등).
bio_long 끝에는 `---tools---` 표식 이후 "활용 도구" 단락이 자동 갱신된다.

Usage:
    cd clickeye-api && uv run python scripts/seed_pm_compositions.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import uuid as uuid_lib

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.pm_composition import PMComposition
from app.models.pm_profile import PMProfile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("seed_pm_compositions")


# ── 매핑 테이블 (도메인 기반) ──────────────────────────────────────────────────

PM_COMPOSITIONS: dict[str, dict[str, list[str]]] = {
    "atlas": {
        "agents": ["harness", "backend", "architect"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "manage-skills", "log-work", "github", "linear"],
        "mcps":   ["postgres", "github", "linear"],
        "hooks":  ["harness-gate", "commit-session", "load-recent-changes"],
    },
    "pixel": {
        "agents": ["harness", "frontend", "uiux"],
        "skills": ["uiux", "ai-critique", "tdd-smart-coding", "fullstack",
                   "log-work", "linear", "github"],
        "mcps":   ["figma", "github", "linear"],
        "hooks":  ["harness-gate", "commit-session", "load-recent-changes"],
    },
    "nova": {
        "agents": ["harness", "fullstack", "frontend", "backend"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "harness-router", "harness-loop", "harness-worker",
                   "harness-context", "ralph-loop", "run-pipeline",
                   "log-work", "linear", "github"],
        "mcps":   ["postgres", "github", "linear", "figma"],
        "hooks":  ["harness-gate", "commit-session", "load-recent-changes"],
    },
    "sentinel": {
        "agents": ["harness", "devops", "security"],
        "skills": ["fullstack", "ai-critique", "manage-skills", "log-work",
                   "github", "run-pipeline"],
        "mcps":   ["github", "jira", "slack"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "forge": {
        "agents": ["harness", "backend", "architect"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "linear"],
        "mcps":   ["postgres", "linear", "github"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "shield": {
        "agents": ["harness", "security", "qa", "lint-python"],
        "skills": ["ai-critique", "tdd-smart-coding", "verify-implementation",
                   "fullstack", "log-work", "jira"],
        "mcps":   ["github", "jira"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "spark": {
        "agents": ["harness", "fullstack", "frontend"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "harness-router", "ralph-loop", "log-work",
                   "linear", "github"],
        "mcps":   ["github", "linear", "slack"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "bridge": {
        "agents": ["harness", "backend", "contracts"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "github", "linear"],
        "mcps":   ["github", "postgres", "linear"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "pulse": {
        "agents": ["harness", "backend", "fullstack"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "slack", "github", "linear"],
        "mcps":   ["postgres", "linear", "github", "slack"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "vision": {
        "agents": ["harness", "fullstack", "docs"],
        "skills": ["fullstack", "ai-critique", "log-work",
                   "manage-skills", "daily-close", "linear"],
        "mcps":   ["postgres", "notion", "linear"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "ops": {
        "agents": ["harness", "fullstack", "backend"],
        "skills": ["fullstack", "ai-critique", "log-work",
                   "manage-skills", "setup", "linear", "github"],
        "mcps":   ["github", "linear", "notion", "slack"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "arena": {
        "agents": ["harness", "backend", "fullstack"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "slack", "github"],
        "mcps":   ["postgres", "github", "slack"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "route": {
        "agents": ["harness", "backend", "fullstack"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "linear", "github"],
        "mcps":   ["postgres", "github", "linear"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "ledger": {
        "agents": ["harness", "backend", "security", "qa"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "verify-implementation", "log-work", "jira", "github"],
        "mcps":   ["postgres", "github", "jira"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "commerce": {
        "agents": ["harness", "fullstack", "frontend", "backend"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "linear", "github"],
        "mcps":   ["postgres", "github", "linear", "figma"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "medic": {
        "agents": ["harness", "backend", "security", "qa"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "verify-implementation", "log-work", "jira", "github"],
        "mcps":   ["postgres", "github", "jira"],
        "hooks":  ["harness-gate", "commit-session", "load-recent-changes"],
    },
    "swift": {
        "agents": ["harness", "frontend", "uiux", "fullstack"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding", "uiux",
                   "log-work", "linear", "github"],
        "mcps":   ["figma", "github", "linear"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "cortex": {
        "agents": ["harness", "backend", "deep-thinker"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "harness-router", "harness-loop", "harness-worker",
                   "harness-context", "ralph-loop", "log-work",
                   "linear", "github", "notion"],
        "mcps":   ["postgres", "notion", "github", "linear"],
        "hooks":  ["harness-gate", "commit-session", "load-recent-changes"],
    },
    "prism": {
        "agents": ["harness", "fullstack", "backend", "frontend"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "manage-skills", "linear", "github"],
        "mcps":   ["postgres", "github", "linear", "slack"],
        "hooks":  ["harness-gate", "commit-session"],
    },
    "nexus": {
        "agents": ["harness", "fullstack", "backend", "frontend"],
        "skills": ["fullstack", "ai-critique", "tdd-smart-coding",
                   "log-work", "linear", "github", "slack"],
        "mcps":   ["postgres", "github", "linear", "slack"],
        "hooks":  ["harness-gate", "commit-session"],
    },
}

# 그룹키 → (테이블명, composition_type)
_GROUP_TABLE_MAP: dict[str, tuple[str, str]] = {
    "agents": ("agents",      "agent"),
    "skills": ("skills",      "skill"),
    "mcps":   ("mcp_servers", "mcp_server"),
    "hooks":  ("hooks",       "hook"),
}

# 화면 표시용 그룹 한국어 라벨 (bio_long 단락에 사용)
_GROUP_LABELS_KO: dict[str, str] = {
    "agents": "AI 에이전트",
    "skills": "스킬",
    "mcps":   "MCP",
    "hooks":  "Hook",
}

# bio_long 자동 갱신 구간 표식
_TOOLS_MARKER = "---tools---"


# ── 헬퍼 ────────────────────────────────────────────────────────────────────────


async def _build_registry_cache(
    db: AsyncSession,
) -> dict[str, dict[str, str]]:
    """레지스트리 4종 테이블에서 slug → name 매핑을 빌드한다.

    Returns:
        {group_key: {slug: name}}  group_key는 "agents"/"skills"/"mcps"/"hooks"
    """
    cache: dict[str, dict[str, str]] = {}
    for group_key, (table_name, _type) in _GROUP_TABLE_MAP.items():
        rows = (await db.execute(
            text(f"SELECT slug, name FROM {table_name}")  # noqa: S608
        )).all()
        cache[group_key] = {str(r[0]): str(r[1]) for r in rows}
    return cache


def _validate_mapping(cache: dict[str, dict[str, str]]) -> list[str]:
    """매핑 테이블의 모든 슬러그가 레지스트리에 존재하는지 검증.

    Returns:
        오류 메시지 리스트. 빈 리스트면 통과.
    """
    errors: list[str] = []
    for pm_slug, groups in PM_COMPOSITIONS.items():
        for group_key, slugs in groups.items():
            if group_key not in cache:
                errors.append(f"{pm_slug}: 알 수 없는 그룹 '{group_key}'")
                continue
            available = cache[group_key]
            for slug in slugs:
                if slug not in available:
                    errors.append(
                        f"{pm_slug}.{group_key}: 슬러그 '{slug}'가 "
                        f"레지스트리에 없음"
                    )
    return errors


def _strip_existing_tools_section(bio_long: str | None) -> str:
    """기존 bio_long에서 ---tools--- 이후 단락을 제거한다 (멱등성)."""
    if not bio_long:
        return ""
    idx = bio_long.find(_TOOLS_MARKER)
    if idx < 0:
        return bio_long.rstrip()
    return bio_long[:idx].rstrip()


def _format_group_line(
    group_key: str,
    slugs: list[str],
    cache: dict[str, dict[str, str]],
) -> str | None:
    """한 그룹의 마크다운 라인을 생성. 빈 그룹은 None."""
    if not slugs:
        return None
    items = []
    for slug in slugs:
        name = cache[group_key].get(slug, slug)
        items.append(f"{name}({slug})")
    label = _GROUP_LABELS_KO[group_key]
    return f"- **{label}**: {', '.join(items)}"


def _compose_tools_block(
    mapping: dict[str, list[str]],
    cache: dict[str, dict[str, str]],
) -> str:
    """bio_long 끝에 추가할 도구 단락을 생성한다."""
    lines = [_TOOLS_MARKER, "", "### 활용 도구", ""]
    for group_key in ("agents", "skills", "mcps", "hooks"):
        line = _format_group_line(group_key, mapping.get(group_key, []), cache)
        if line is not None:
            lines.append(line)
    return "\n".join(lines)


# ── 메인 실행 ───────────────────────────────────────────────────────────────────


async def seed() -> None:
    async with async_session() as db:
        # 1. 레지스트리 캐시 빌드
        logger.info("레지스트리 캐시 빌드 중...")
        cache = await _build_registry_cache(db)
        for group_key, items in cache.items():
            logger.info("  %s: %d개", group_key, len(items))

        # 2. 매핑 검증 (오타 방지)
        errors = _validate_mapping(cache)
        if errors:
            logger.error("매핑 검증 실패 (%d건):", len(errors))
            for e in errors:
                logger.error("  - %s", e)
            sys.exit(1)
        logger.info("매핑 검증 통과: PM %d개", len(PM_COMPOSITIONS))

        # 3. PM별 처리
        applied = 0
        skipped: list[str] = []
        for pm_slug, mapping in PM_COMPOSITIONS.items():
            pm = (await db.execute(
                select(PMProfile).where(PMProfile.slug == pm_slug)
            )).scalar_one_or_none()
            if pm is None:
                skipped.append(pm_slug)
                logger.warning("PM 없음, 건너뜀: %s", pm_slug)
                continue

            # 3-a. 기존 composition 모두 삭제
            await db.execute(
                delete(PMComposition).where(PMComposition.pm_id == pm.id)
            )

            # 3-b. 새 composition 등록
            for group_key, (_table, component_type) in _GROUP_TABLE_MAP.items():
                slugs = mapping.get(group_key, [])
                for order, slug in enumerate(slugs):
                    db.add(PMComposition(
                        id=uuid_lib.uuid4(),
                        pm_id=pm.id,
                        component_type=component_type,
                        component_slug=slug,
                        component_name=cache[group_key].get(slug, slug),
                        config={},
                        display_order=order,
                        is_required=False,
                    ))

            # 3-c. bio_long 갱신 — 기존 도구 단락 제거 후 새로 추가
            existing_bio = _strip_existing_tools_section(pm.bio_long)
            tools_block = _compose_tools_block(mapping, cache)
            new_bio = f"{existing_bio}\n\n{tools_block}" if existing_bio else tools_block
            await db.execute(
                update(PMProfile)
                .where(PMProfile.id == pm.id)
                .values(bio_long=new_bio)
            )

            counts = {k: len(mapping.get(k, [])) for k in _GROUP_TABLE_MAP}
            logger.info(
                "  %-10s — agents=%d skills=%d mcps=%d hooks=%d",
                pm_slug, counts["agents"], counts["skills"],
                counts["mcps"], counts["hooks"],
            )
            applied += 1

        # 4. 단일 커밋
        await db.commit()
        logger.info("커밋 완료: %d개 PM 재구성", applied)
        if skipped:
            logger.warning("건너뛴 PM (%d): %s", len(skipped), ", ".join(skipped))


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
