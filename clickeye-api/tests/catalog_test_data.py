"""테스트용 정적 카탈로그 + handcrafted prefetch 빌더.

실 카탈로그(DB)는 테스트에서 시드되지 않으므로, generate_all 의 **emit 로직**을
검증하기 위한 최소 prefetch 를 만든다.

주의: selection(어떤 slug 가 포함되는지)은 prefetch_for_generator(DB)의 책임이고
generate_all/get_selected_* 는 prefetch 내용을 그대로 emit 한다. 따라서 여기 테스트는
"prefetch → 산출물" emit-regression 만 검증한다(실 selection 커버리지가 아님).
계약값(output_file / env_var 이름 / agent output_file)만 실제 카탈로그와 맞춘다.
"""

from typing import Any

from app.engine.catalog import CatalogPrefetch
from app.engine.generator import generate_all

# 실 계약값에 맞춘 최소 스킬 (id=slug, output_file, env_vars 이름)
_SKILLS: dict[str, dict[str, Any]] = {
    "linear": {
        "id": "linear",
        "label": "Linear",
        "output_file": "linear-sync.md",
        "body_md": "# Linear Sync\n\nLinear 이슈 트래킹 연동 스킬(테스트 카탈로그).",
        "env_vars": [
            {"name": "LINEAR_API_KEY", "required": True, "description": "Linear API key"},
            {"name": "LINEAR_TEAM_ID", "required": True, "description": "Linear Team ID"},
        ],
    },
    "notion": {
        "id": "notion",
        "label": "Notion",
        "output_file": "notion-sync.md",
        "body_md": "# Notion Sync\n\nNotion 워크스페이스 연동 스킬(테스트 카탈로그).",
        "env_vars": [
            {"name": "NOTION_API_KEY", "required": True, "description": "Notion API key"},
            {"name": "NOTION_DATABASE_ID", "required": True, "description": "Notion DB ID"},
        ],
    },
    "tdd-smart-coding": {
        "id": "tdd-smart-coding",
        "label": "TDD Smart Coding",
        "output_file": "tdd-smart-coding.md",
        "body_md": "# TDD Smart Coding\n\n테스트 우선 개발 스킬(테스트 카탈로그).",
        "env_vars": [],
    },
}

# 실 계약값에 맞춘 최소 에이전트 (backend → api-agent.md)
_AGENTS: dict[str, dict[str, Any]] = {
    "backend": {
        "id": "backend",
        "label": "Backend",
        "output_file": "api-agent.md",
        "body_md": "# Backend Agent\n\n백엔드 API 개발 가이드(테스트 카탈로그).",
    },
    "frontend": {
        "id": "frontend",
        "label": "Frontend",
        "output_file": "web-agent.md",
        "body_md": "# Frontend Agent\n\n프론트엔드 개발 가이드(테스트 카탈로그).",
    },
}


def build_test_prefetch(
    skill_slugs: tuple[str, ...] | list[str] = (),
    agent_slugs: tuple[str, ...] | list[str] = (),
    locale: str = "ko",
) -> CatalogPrefetch:
    """주어진 slug 에 해당하는 정적 스킬/에이전트로 CatalogPrefetch 구성."""
    skills = [dict(_SKILLS[s]) for s in skill_slugs if s in _SKILLS]
    agents = [dict(_AGENTS[a]) for a in agent_slugs if a in _AGENTS]
    return CatalogPrefetch(agents=agents, skills=skills, hooks=[], mcps=[], locale=locale)


def emit_files(
    *,
    skills: tuple[str, ...] | list[str] = (),
    agents: tuple[str, ...] | list[str] = (),
    prefetch: CatalogPrefetch | None = None,
    platform: str = "claude-code",
    pm_slug: str | None = None,
    pm_markdown: str | None = None,
    pm_compositions: list[dict[str, Any]] | None = None,
    project_name: str = "catalog-emit-test",
    stack_id: str = "fastapi-nextjs",
) -> dict[str, str | bytes]:
    """generate_all 을 직접 호출해 emit 결과(files dict)를 반환(ZIP 래핑 없이)."""
    return generate_all(
        project_name=project_name,
        project_type="fullstack",
        stack_id=stack_id,
        agent_ids=list(agents),
        workflow_ids=list(skills),
        platform_id=platform,
        os_id="wsl2",
        pm_slug=pm_slug,
        pm_markdown=pm_markdown,
        pm_compositions=pm_compositions,
        catalog_prefetch=prefetch,
    )
