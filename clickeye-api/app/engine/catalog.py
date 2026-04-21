"""생성 엔진용 카탈로그 데이터."""

from typing import Any

# 에이전트 카탈로그 (web 엔진과 동일 구조)
AGENTS: list[dict[str, Any]] = [
    {
        "id": "backend",
        "name": "시니어 백엔드 엔지니어",
        "description": "API 설계, DB, 서버 로직 전담",
        "output_file": "api-agent.md",
        "template": "agents/api-agent.md.j2",
        "required": False,
    },
    {
        "id": "frontend",
        "name": "프론트엔드 전문가",
        "description": "컴포넌트, 상태관리, 라우팅 전담",
        "output_file": "web-agent.md",
        "template": "agents/web-agent.md.j2",
        "required": False,
    },
    {
        "id": "uiux",
        "name": "UI/UX 디자이너",
        "description": "접근성, 반응형, 디자인 시스템 전담",
        "output_file": "uiux-agent.md",
        "template": "agents/uiux-agent.md.j2",
        "required": False,
    },
    {
        "id": "devops",
        "name": "DevOps 엔지니어",
        "description": "Docker, CI/CD, 배포 전담",
        "output_file": "infra-agent.md",
        "template": "agents/infra-agent.md.j2",
        "required": False,
    },
    {
        "id": "fullstack",
        "name": "풀스택 시니어",
        "description": "백엔드+프론트 통합 개발",
        "output_file": "fullstack-agent.md",
        "template": "agents/fullstack-agent.md.j2",
        "required": False,
    },
    {
        "id": "harness",
        "name": "하네스 엔지니어 (필수)",
        "description": "4단계 품질 통제 — Router→Context→Loop→Worker",
        "output_file": "harness-guide.md",
        "template": "agents/harness-guide.md.j2",
        "required": True,
    },
]

# 스킬/워크플로우 카탈로그
SKILLS: list[dict[str, Any]] = [
    {
        "id": "tdd",
        "name": "TDD 스마트 코딩",
        "template": "skills/tdd.md.j2",
        "output_file": "tdd-smart-coding.md",
        "dependencies": [],
        "hooks": [],
    },
    {
        "id": "ai-critique",
        "name": "AI 코드 리뷰",
        "template": "skills/ai-critique.md.j2",
        "output_file": "ai-critique.md",
        "dependencies": [],
        "hooks": ["PostToolUse"],
    },
    {
        "id": "linear",
        "name": "Linear 연동",
        "template": "skills/linear.md.j2",
        "output_file": "linear-sync.md",
        "dependencies": ["linear"],
        "hooks": [],
        "category": "ticket_source",
        "env_vars": [
            {
                "name": "LINEAR_API_KEY",
                "description": "Linear API 토큰 (Settings → API → Personal API keys)",
                "pattern": r"^lin_api_[A-Za-z0-9]+$",
                "required": True,
            },
            {
                "name": "LINEAR_TEAM_ID",
                "description": "Linear 팀 UUID (API로 조회 또는 URL에서 확인)",
                "pattern": "",
                "required": True,
            },
        ],
    },
    {
        "id": "notion",
        "name": "Notion 연동",
        "template": "skills/notion.md.j2",
        "output_file": "notion-sync.md",
        "dependencies": ["notion"],
        "hooks": [],
        "category": "ticket_source",
        "env_vars": [
            {
                "name": "NOTION_API_KEY",
                "description": "Notion Integration 토큰 (notion.so/my-integrations에서 발급)",
                "pattern": r"^secret_[A-Za-z0-9]+$",
                "required": True,
            },
            {
                "name": "NOTION_DATABASE_ID",
                "description": "Notion 데이터베이스 ID (데이터베이스 URL의 32자리 UUID)",
                "pattern": "",
                "required": True,
            },
        ],
    },
    {
        "id": "ralph-loop",
        "name": "Ralph 자율 루프",
        "template": "skills/ralph-loop.md.j2",
        "output_file": "ralph-loop.md",
        "dependencies": [],
        "hooks": [],
    },
    {
        "id": "harness-gate",
        "name": "하네스 Gate",
        "template": "skills/harness-gate.md.j2",
        "output_file": "harness-gate.md",
        "dependencies": [],
        "hooks": ["UserPromptSubmit"],
    },
]

# 기술 스택 카탈로그
STACKS: list[dict[str, Any]] = [
    {
        "id": "fastapi-nextjs",
        "name": "FastAPI + Next.js",
        "backend": "FastAPI + SQLAlchemy",
        "frontend": "Next.js 15 + Tailwind",
        "test": {"backend": "uv run pytest --tb=short -q", "frontend": "npm run test"},
        "lint": {"backend": "uv run ruff check .", "frontend": "npm run lint"},
        "typecheck": {"backend": "uv run mypy app/", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "django-react",
        "name": "Django + React",
        "backend": "Django + DRF",
        "frontend": "React + Vite",
        "test": {"backend": "uv run pytest --tb=short -q", "frontend": "npm run test"},
        "lint": {"backend": "uv run ruff check .", "frontend": "npm run lint"},
        "typecheck": {"backend": "uv run mypy .", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "express-vue",
        "name": "Express + Vue",
        "backend": "Express + Prisma",
        "frontend": "Vue 3 + Vite",
        "test": {"backend": "npm run test:backend", "frontend": "npm run test"},
        "lint": {"backend": "npx eslint src/", "frontend": "npm run lint"},
        "typecheck": {"backend": "npx tsc --noEmit", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "nestjs-nextjs",
        "name": "NestJS + Next.js",
        "backend": "NestJS + TypeORM",
        "frontend": "Next.js 15",
        "test": {"backend": "npm run test:backend", "frontend": "npm run test"},
        "lint": {"backend": "npx eslint src/", "frontend": "npm run lint"},
        "typecheck": {"backend": "npx tsc --noEmit", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "flask-react",
        "name": "Flask + React",
        "backend": "Flask + SQLAlchemy",
        "frontend": "React + Vite",
        "test": {"backend": "uv run pytest --tb=short -q", "frontend": "npm run test"},
        "lint": {"backend": "uv run ruff check .", "frontend": "npm run lint"},
        "typecheck": {"backend": "uv run mypy .", "frontend": "npx tsc --noEmit"},
    },
    {
        "id": "custom",
        "name": "커스텀 (직접 입력)",
        "backend": "",
        "frontend": "",
        "test": {"backend": "", "frontend": ""},
        "lint": {"backend": "", "frontend": ""},
        "typecheck": {"backend": "", "frontend": ""},
    },
]


def get_env_var_definitions(workflow_ids: list[str]) -> list[dict[str, Any]]:
    """선택된 워크플로우에서 필요한 환경 변수 정의를 수집."""
    skills = get_selected_skills(workflow_ids)
    env_vars: list[dict[str, Any]] = []
    seen: set[str] = set()
    for skill in skills:
        for var in skill.get("env_vars", []):
            if var["name"] not in seen:
                env_vars.append({**var, "skill_id": skill["id"], "skill_name": skill["name"]})
                seen.add(var["name"])
    return env_vars


def find_stack(stack_id: str) -> dict[str, Any] | None:
    """스택 ID로 카탈로그 항목 검색."""
    return next((s for s in STACKS if s["id"] == stack_id), None)


def get_selected_agents(agent_ids: list[str]) -> list[dict[str, Any]]:
    """선택된 에이전트 + required 에이전트 반환."""
    return [a for a in AGENTS if a["id"] in agent_ids or a.get("required")]


def get_selected_skills(workflow_ids: list[str]) -> list[dict[str, Any]]:
    """선택된 워크플로우에 해당하는 스킬 반환."""
    return [s for s in SKILLS if s["id"] in workflow_ids]
