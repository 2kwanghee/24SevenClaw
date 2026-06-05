"""테스트용 정적 카탈로그 + 두 전달 경로(prefetch 주입 / ORM 시드).

실 카탈로그(DB)는 테스트에서 시드되지 않으므로, generate_all 의 **emit 로직**을
검증하기 위한 최소 카탈로그를 만든다. 두 가지로 전달한다:
- 직접호출 테스트 → `emit_files(prefetch=build_test_prefetch(...))`
- 엔드포인트/DB 테스트 → `seed_catalog_db(db_session)` (registry 모델 ORM insert)

주의: selection 은 prefetch_for_generator(DB) 책임, generate_all 은 prefetch 를 그대로 emit.
계약값(output_file / env_var 이름 / agent output_file)만 실제 카탈로그와 맞춘다.
"""

from typing import TYPE_CHECKING, Any

from app.engine.catalog import CatalogPrefetch
from app.engine.generator import generate_all

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

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
    "harness-gate": {
        "id": "harness-gate",
        "label": "Harness Gate",
        "output_file": "harness-gate.md",
        "body_md": "# Harness Gate\n\n품질 게이트 스킬(테스트 카탈로그).",
        "env_vars": [],
    },
}

# 실 계약값에 맞춘 최소 에이전트. backend body 는 project_name/stack 렌더 검증용 템플릿 변수 포함.
_AGENTS: dict[str, dict[str, Any]] = {
    "backend": {
        "id": "backend",
        "label": "Backend",
        "output_file": "api-agent.md",
        "body_md": "# {{ project_name }} Backend Agent\n스택: {{ stack.backend }}",
    },
    "frontend": {
        "id": "frontend",
        "label": "Frontend",
        "output_file": "web-agent.md",
        "body_md": "# {{ project_name }} Frontend Agent\n프론트엔드 가이드(테스트).",
    },
    "harness": {
        "id": "harness",
        "label": "Harness",
        "output_file": "harness-guide.md",
        "body_md": "# Harness Guide\n\n하네스 엔지니어링 가이드(테스트 카탈로그).",
        "required": True,
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
    project_type: str = "fullstack",
    stack_id: str = "fastapi-nextjs",
) -> dict[str, str | bytes]:
    """generate_all 을 직접 호출해 emit 결과(files dict)를 반환(ZIP 래핑 없이)."""
    return generate_all(
        project_name=project_name,
        project_type=project_type,
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


async def seed_catalog_db(db_session: "AsyncSession") -> None:
    """엔드포인트/DB 테스트용 — TEST_CATALOG 를 registry 모델로 ORM insert 후 commit.

    prefetch_for_generator(db) 가 slug 로 조회하므로, 이 시드 후 엔드포인트 생성 흐름이
    동일 카탈로그를 사용한다. (실 전체 카탈로그가 아닌 테스트용 최소 집합)
    """
    from app.models.registry import Agent, Skill

    for a in _AGENTS.values():
        db_session.add(
            Agent(
                slug=a["id"],
                name=a.get("label", a["id"]),
                output_file=a.get("output_file"),
                body_md=a.get("body_md"),
                required=a.get("required", False),
                is_public=True,
            )
        )
    for s in _SKILLS.values():
        db_session.add(
            Skill(
                slug=s["id"],
                name=s.get("label", s["id"]),
                output_file=s.get("output_file"),
                body_md=s.get("body_md"),
                env_vars=s.get("env_vars", []),
                is_public=True,
            )
        )
    await db_session.commit()
