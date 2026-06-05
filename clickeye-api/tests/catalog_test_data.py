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

# 실 계약값에 맞춘 공개 스킬 6종 (id=slug, label, description, output_file, env_vars 이름).
# 엔드포인트 구조 테스트는 total==6 + 각 항목 id/label/description(str) 을 검증한다.
_SKILLS: dict[str, dict[str, Any]] = {
    "linear": {
        "id": "linear",
        "label": "Linear",
        "description": "Linear 이슈 트래킹 연동 스킬(테스트 카탈로그).",
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
        "description": "Notion 워크스페이스 연동 스킬(테스트 카탈로그).",
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
        "description": "테스트 우선 개발 스킬(테스트 카탈로그).",
        "output_file": "tdd-smart-coding.md",
        "body_md": "# TDD Smart Coding\n\n테스트 우선 개발 스킬(테스트 카탈로그).",
        "env_vars": [],
    },
    "harness-gate": {
        "id": "harness-gate",
        "label": "Harness Gate",
        "description": "품질 게이트 스킬(테스트 카탈로그).",
        "output_file": "harness-gate.md",
        "body_md": "# Harness Gate\n\n품질 게이트 스킬(테스트 카탈로그).",
        "env_vars": [],
    },
    "ai-critique": {
        "id": "ai-critique",
        "label": "AI 코드 리뷰",
        "description": "외부 AI(GPT, Gemini)에 코드 리뷰를 요청하는 스킬(테스트 카탈로그).",
        "output_file": "ai-critique.md",
        "body_md": "# AI Critique\n\n외부 AI 코드 리뷰 스킬(테스트 카탈로그).",
        "env_vars": [],
    },
    "ralph-loop": {
        "id": "ralph-loop",
        "label": "Ralph 자율 개발 루프",
        "description": "fix_plan.md 기반 자율 반복 개발 루프 스킬(테스트 카탈로그).",
        "output_file": "ralph-loop.md",
        "body_md": "# Ralph Loop\n\n자율 반복 개발 루프 스킬(테스트 카탈로그).",
        "env_vars": [],
    },
}

# 실 계약값에 맞춘 공개 에이전트 7종 (agents.json 기준). backend body 는
# project_name/stack 렌더 검증용 템플릿 변수 포함. output_file 은 023 마이그레이션 매핑.
# 엔드포인트 구조 테스트는 total==7 + 각 항목 id/label/description(str) 을 검증한다.
_AGENTS: dict[str, dict[str, Any]] = {
    "backend": {
        "id": "backend",
        "label": "Backend",
        "description": "API/서버 로직 전담(테스트 카탈로그).",
        "output_file": "api-agent.md",
        "body_md": "# {{ project_name }} Backend Agent\n스택: {{ stack.backend }}",
    },
    "frontend": {
        "id": "frontend",
        "label": "Frontend",
        "description": "UI/UX 구현 전담(테스트 카탈로그).",
        "output_file": "web-agent.md",
        "body_md": "# {{ project_name }} Frontend Agent\n프론트엔드 가이드(테스트).",
    },
    "harness": {
        "id": "harness",
        "label": "Harness",
        "description": "코드 품질 게이트(테스트 카탈로그).",
        "output_file": "harness-guide.md",
        "body_md": "# Harness Guide\n\n하네스 엔지니어링 가이드(테스트 카탈로그).",
        "required": True,
    },
    "architect": {
        "id": "architect",
        "label": "Architect",
        "description": "시스템 설계 전담(테스트 카탈로그).",
        "output_file": "architect.md",
        "body_md": "# Architect Agent\n\n시스템 아키텍처 설계 가이드(테스트 카탈로그).",
    },
    "qa": {
        "id": "qa",
        "label": "QA",
        "description": "테스트 자동화 전담(테스트 카탈로그).",
        "output_file": "qa.md",
        "body_md": "# QA Agent\n\n테스트 자동화 가이드(테스트 카탈로그).",
    },
    "devops": {
        "id": "devops",
        "label": "DevOps",
        "description": "인프라/배포 전담(테스트 카탈로그).",
        "output_file": "infra-agent.md",
        "body_md": "# DevOps Agent\n\n인프라/배포 가이드(테스트 카탈로그).",
    },
    "security": {
        "id": "security",
        "label": "Security",
        "description": "보안 감사 전담(테스트 카탈로그).",
        "output_file": "security.md",
        "body_md": "# Security Agent\n\n보안 감사 가이드(테스트 카탈로그).",
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
                description=a.get("description"),
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
                description=s.get("description"),
                output_file=s.get("output_file"),
                body_md=s.get("body_md"),
                env_vars=s.get("env_vars", []),
                is_public=True,
            )
        )
    await db_session.commit()
