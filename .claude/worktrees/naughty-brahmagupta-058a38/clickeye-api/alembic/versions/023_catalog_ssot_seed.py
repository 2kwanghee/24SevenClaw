"""카탈로그 DB-SSOT 전환 — agents 16종 / skills 22종 / hooks 3종 시드 데이터 삽입

agents·skills·hooks를 ON CONFLICT DO UPDATE(upsert)로 삽입하여 멱등성 보장.
body_md 는 CLAUDE_DIR 환경변수(없으면 알려진 경로들을 순서대로 탐색)에서 .claude/ 파일을 읽어 채운다.
파일이 없으면 null 로 삽입하고, ZIP 엔진이 j2 파일 fallback 을 사용한다.

Revision ID: 023
Revises: 022
Create Date: 2026-04-23 00:00:00.000000
"""

import os
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = datetime(2026, 4, 23, tzinfo=UTC)

# .claude/ 디렉토리 탐색 순서 (환경변수 → 알려진 로컬 경로들)
_CLAUDE_DIR_CANDIDATES = [
    os.environ.get("CLAUDE_DIR", ""),
    "/mnt/c/workspace/ClickEye/.claude",
    str(Path(__file__).parents[4] / ".claude"),  # 레포 루트/../.claude
]


def _find_claude_dir() -> Path | None:
    for candidate in _CLAUDE_DIR_CANDIDATES:
        if candidate and (p := Path(candidate)).is_dir():
            return p
    return None


def _read_md(claude_dir: Path | None, rel: str) -> str | None:
    if claude_dir is None:
        return None
    p = claude_dir / rel
    if p.is_file():
        return p.read_text(encoding="utf-8")
    return None


_CLAUDE = _find_claude_dir()

# ─── 에이전트 카탈로그 (16종) ────────────────────────────────────────────────
# (slug, name, description, output_file, category, required, body_md_rel)
_AGENTS: list[tuple[str, str, str, str, str, bool, str]] = [
    ("backend", "시니어 백엔드 엔지니어", "API 설계, DB, 서버 로직 전담", "api-agent.md", "core", False, "agents/api-agent.md"),
    ("frontend", "프론트엔드 전문가", "컴포넌트, 상태관리, 라우팅 전담", "web-agent.md", "core", False, "agents/web-agent.md"),
    ("uiux", "UI/UX 디자이너", "접근성, 반응형, 디자인 시스템 전담", "uiux-agent.md", "domain", False, "agents/uiux-agent.md"),
    ("devops", "DevOps 엔지니어", "Docker, CI/CD, 배포 전담", "infra-agent.md", "core", False, "agents/infra-agent.md"),
    ("fullstack", "풀스택 시니어", "백엔드+프론트 통합 개발", "fullstack-agent.md", "domain", False, ""),
    ("harness", "하네스 엔지니어 (필수)", "4단계 품질 통제 — Router→Context→Loop→Worker", "harness-guide.md", "core", True, "agents/harness-guide.md"),
    ("architect", "시스템 아키텍트", "아키텍처 설계, 기술 결정, 장기 유지보수 전략", "architect.md", "core", False, ""),
    ("qa", "QA 엔지니어", "테스트 자동화, 품질 보증", "qa.md", "quality", False, ""),
    ("security", "보안 감사관", "취약점 분석, 보안 정책, 컴플라이언스", "security.md", "quality", False, ""),
    ("pm-agent", "PM 에이전트", "세션 시작 & 복잡도 분석 → 구현 스펙 생성", "pm-agent.md", "meta", False, "agents/pm-agent.md"),
    ("deep-thinker", "딥 씽커", "복잡한 설계/트레이드오프 분석 (pm-agent 위임)", "deep-thinker.md", "meta", False, "agents/deep-thinker.md"),
    ("docs", "문서 작성 에이전트", "docs/, CLAUDE.md, README.md 등 문서 작업", "docs.md", "meta", False, "agents/docs.md"),
    ("lint-frontend", "프론트엔드 린터", "ESLint, TypeScript 타입 체크 실행", "lint-frontend.md", "quality", False, "agents/lint-frontend.md"),
    ("lint-python", "파이썬 린터", "ruff check/format, mypy 타입 체크 실행", "lint-python.md", "quality", False, "agents/lint-python.md"),
    ("agent-agent", "에이전트 빌더", "Claude Code 에이전트 설계 및 개선 전담", "agent-agent.md", "meta", False, "agents/agent-agent.md"),
    ("contracts", "계약 관리 에이전트", "공유 타입/프로토콜 계약 관리", "contracts-agent.md", "meta", False, "agents/contracts-agent.md"),
]

# ─── 스킬 카탈로그 (22종) ────────────────────────────────────────────────────
# (slug, name, description, output_file, category, required, hook_events, env_vars, body_md_rel)
_LINEAR_ENV: list[dict[str, Any]] = [
    {"name": "LINEAR_API_KEY", "description": "Linear API 토큰 (Settings → API → Personal API keys)", "pattern": "^lin_api_[A-Za-z0-9]+$", "required": True},
    {"name": "LINEAR_TEAM_ID", "description": "Linear 팀 UUID (API로 조회 또는 URL에서 확인)", "pattern": "", "required": True},
]
_NOTION_ENV: list[dict[str, Any]] = [
    {"name": "NOTION_API_KEY", "description": "Notion Integration 토큰 (notion.so/my-integrations에서 발급)", "pattern": "^secret_[A-Za-z0-9]+$", "required": True},
    {"name": "NOTION_DATABASE_ID", "description": "Notion 데이터베이스 ID (데이터베이스 URL의 32자리 UUID)", "pattern": "", "required": True},
]
_TELEGRAM_ENV: list[dict[str, Any]] = [
    {"name": "TELEGRAM_BOT_TOKEN", "description": "Telegram Bot Token (@BotFather에서 발급)", "pattern": "", "required": True},
    {"name": "TELEGRAM_CHAT_ID", "description": "알림을 보낼 채팅방/채널 ID", "pattern": "", "required": True},
]
_GITHUB_ENV: list[dict[str, Any]] = [
    {"name": "GITHUB_TOKEN", "description": "GitHub Personal Access Token", "pattern": "", "required": True},
    {"name": "GITHUB_REPO", "description": "리포지토리 (owner/repo 형식)", "pattern": "", "required": True},
]
_SLACK_ENV: list[dict[str, Any]] = [
    {"name": "SLACK_BOT_TOKEN", "description": "Slack Bot Token (xoxb-...)", "pattern": "^xoxb-", "required": True},
    {"name": "SLACK_CHANNEL", "description": "알림을 보낼 채널 ID 또는 이름", "pattern": "", "required": True},
]
_JIRA_ENV: list[dict[str, Any]] = [
    {"name": "JIRA_URL", "description": "Jira 인스턴스 URL (https://yourcompany.atlassian.net)", "pattern": "", "required": True},
    {"name": "JIRA_API_TOKEN", "description": "Jira API Token (계정 설정에서 발급)", "pattern": "", "required": True},
    {"name": "JIRA_EMAIL", "description": "Jira 계정 이메일", "pattern": "", "required": True},
    {"name": "JIRA_PROJECT_KEY", "description": "Jira 프로젝트 키 (예: PROJ)", "pattern": "", "required": True},
]

_SKILLS: list[tuple[str, str, str, str, str, bool, list, list[dict], str]] = [
    # slug, name, desc, output_file, category, required, hook_events, env_vars, body_md_rel
    ("linear", "Linear 연동", "Linear 이슈 트래킹 연동", "linear-sync.md", "ticket_source", False, [], _LINEAR_ENV, ""),
    ("notion", "Notion 연동", "Notion 워크스페이스 연동", "notion-sync.md", "ticket_source", False, [], _NOTION_ENV, ""),
    ("telegram", "Telegram 알림", "Telegram 봇 알림 연동", "telegram.md", "notification", False, [], _TELEGRAM_ENV, ""),
    ("github", "GitHub 연동", "GitHub 리포지토리 연동", "github.md", "vcs", False, [], _GITHUB_ENV, ""),
    ("slack", "Slack 알림", "Slack 채널 알림 연동", "slack.md", "notification", False, [], _SLACK_ENV, ""),
    ("jira", "Jira 연동", "Jira 이슈 트래킹 연동", "jira.md", "ticket_source", False, [], _JIRA_ENV, ""),
    ("tdd-smart-coding", "TDD 스마트 코딩", "테스트 주도 개발 워크플로", "tdd-smart-coding.md", "quality", False, [], [], "skills/tdd-smart-coding/SKILL.md"),
    ("ai-critique", "AI 코드 리뷰", "PostToolUse 훅 기반 자동 코드 리뷰", "ai-critique.md", "quality", False, ["PostToolUse"], [], "skills/ai-critique/SKILL.md"),
    ("ralph-loop", "Ralph 자율 루프", "자율 반복 개선 루프", "ralph-loop.md", "pipeline", False, [], [], "skills/ralph-loop/SKILL.md"),
    ("harness-gate", "하네스 게이트", "UserPromptSubmit 훅 기반 코드 품질 게이트", "harness-gate.md", "pipeline", False, ["UserPromptSubmit"], [], ""),
    ("daily-close", "일일 마감", "하루 작업 정리 및 Daily Close 루틴", "daily-close.md", "ops", False, [], [], "skills/daily-close/SKILL.md"),
    ("endwork", "작업 종료", "세션 종료 시 작업 정리 루틴", "endwork.md", "ops", False, [], [], "skills/endwork/SKILL.md"),
    ("fullstack", "풀스택 개발", "풀스택 개발 워크플로 (백엔드+프론트엔드)", "fullstack.md", "pipeline", False, [], [], "skills/fullstack/SKILL.md"),
    ("harness-context", "하네스 컨텍스트", "필요한 정보만 선별 제공하는 컨텍스트 관리자", "harness-context.md", "pipeline", False, [], [], "skills/harness-context/SKILL.md"),
    ("harness-loop", "하네스 루프", "코드작성→테스트→실패시 수정 반복 루프 (MAX 5회)", "harness-loop.md", "pipeline", False, [], [], "skills/harness-loop/SKILL.md"),
    ("harness-router", "하네스 라우터", "의도 분석: 모호→되물어보기 / 명확→루프 / 대화→표준응답", "harness-router.md", "pipeline", False, [], [], "skills/harness-router/SKILL.md"),
    ("harness-worker", "하네스 워커", "WRITE_CODE / TEST_WRITER / CODE_REVIEW / SECURITY_REVIEW 역할 분리", "harness-worker.md", "pipeline", False, [], [], "skills/harness-worker/SKILL.md"),
    ("log-work", "작업 로그", "작업 완료 후 Linear/Notion에 자동 로그 기록", "log-work.md", "ops", False, [], [], "skills/log-work/SKILL.md"),
    ("manage-skills", "스킬 관리", "스킬 목록 조회, 설치, 업데이트", "manage-skills.md", "ops", False, [], [], "skills/manage-skills/SKILL.md"),
    ("merge-worktree", "워크트리 머지", "Git worktree 기반 병렬 작업 후 머지 전략", "merge-worktree.md", "vcs", False, [], [], "skills/merge-worktree/SKILL.md"),
    ("prd-to-linear", "PRD → Linear", "PRD 문서에서 Linear 이슈 자동 생성", "prd-to-linear.md", "ticket_source", False, [], _LINEAR_ENV, "skills/prd-to-linear/SKILL.md"),
    ("run-pipeline", "파이프라인 실행", "자동화 파이프라인 실행 및 결과 처리", "run-pipeline.md", "pipeline", False, [], [], "skills/run-pipeline/SKILL.md"),
    ("setup", "초기 셋업", "프로젝트 초기 셋업 및 환경 설정", "setup.md", "ops", False, [], [], "skills/setup/SKILL.md"),
    ("uiux", "UI/UX 스킬", "Figma MCP 연동, 디자인 체크리스트, 접근성 검증", "uiux.md", "quality", False, [], [], "skills/uiux/SKILL.md"),
    ("verify-implementation", "구현 검증", "구현 완료 후 요구사항 충족 여부 검증", "verify-implementation.md", "quality", False, [], [], "skills/verify-implementation/SKILL.md"),
]

# ─── 훅 카탈로그 (3종) ──────────────────────────────────────────────────────
# (slug, name, description, output_file, event, category, required, body_md_rel)
_HOOKS: list[tuple[str, str, str, str, str, str, bool, str]] = [
    ("harness-gate", "하네스 게이트", "사용자 요청마다 컨텍스트 점검 및 품질 게이트 실행", "scripts/harness-gate.sh", "UserPromptSubmit", "quality", False, "hooks/harness-gate.sh"),
    ("commit-session", "커밋 세션", "작업 완료 후 세션 정보를 자동 커밋 메시지에 포함", "scripts/commit-session.sh", "Stop", "ops", False, "hooks/commit-session.sh"),
    ("load-recent-changes", "최근 변경 로드", "세션 시작 시 최근 변경사항을 컨텍스트에 자동 로드", "scripts/load-recent-changes.sh", "UserPromptSubmit", "ops", False, "hooks/load-recent-changes.sh"),
]


def upgrade() -> None:
    conn = op.get_bind()

    # agents upsert
    for slug, name, desc, output_file, category, required, body_md_rel in _AGENTS:
        body_md = _read_md(_CLAUDE, body_md_rel) if body_md_rel else None
        conn.execute(
            sa.text(
                """
                INSERT INTO agents
                    (id, name, slug, description, output_file, category, required,
                     body_md, version, is_public, dependencies, config_schema,
                     created_at, updated_at)
                VALUES
                    (:id, :name, :slug, :desc, :output_file, :category, :required,
                     :body_md, '0.1.0', TRUE, '[]', '{}',
                     :now, :now)
                ON CONFLICT (slug) DO UPDATE SET
                    name        = EXCLUDED.name,
                    description = EXCLUDED.description,
                    output_file = EXCLUDED.output_file,
                    category    = EXCLUDED.category,
                    required    = EXCLUDED.required,
                    body_md     = COALESCE(EXCLUDED.body_md, agents.body_md),
                    updated_at  = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slug,
                "desc": desc,
                "output_file": output_file,
                "category": category,
                "required": required,
                "body_md": body_md,
                "now": _NOW,
            },
        )

    # skills upsert
    import json  # noqa: PLC0415

    for slug, name, desc, output_file, category, required, hook_events, env_vars, body_md_rel in _SKILLS:
        body_md = _read_md(_CLAUDE, body_md_rel) if body_md_rel else None
        conn.execute(
            sa.text(
                """
                INSERT INTO skills
                    (id, name, slug, description, output_file, category, required,
                     body_md, hook_events, env_vars, version, is_public,
                     dependencies, config_schema, created_at, updated_at)
                VALUES
                    (:id, :name, :slug, :desc, :output_file, :category, :required,
                     :body_md, :hook_events, :env_vars, '0.1.0', TRUE,
                     '[]', '{}', :now, :now)
                ON CONFLICT (slug) DO UPDATE SET
                    name        = EXCLUDED.name,
                    description = EXCLUDED.description,
                    output_file = EXCLUDED.output_file,
                    category    = EXCLUDED.category,
                    required    = EXCLUDED.required,
                    body_md     = COALESCE(EXCLUDED.body_md, skills.body_md),
                    hook_events = EXCLUDED.hook_events,
                    env_vars    = EXCLUDED.env_vars,
                    updated_at  = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slug,
                "desc": desc,
                "output_file": output_file,
                "category": category,
                "required": required,
                "body_md": body_md,
                "hook_events": json.dumps(hook_events),
                "env_vars": json.dumps(env_vars),
                "now": _NOW,
            },
        )

    # hooks upsert
    for slug, name, desc, output_file, event, category, required, body_md_rel in _HOOKS:
        body_md = _read_md(_CLAUDE, body_md_rel) if body_md_rel else None
        conn.execute(
            sa.text(
                """
                INSERT INTO hooks
                    (id, name, slug, description, output_file, event, category, required,
                     body_md, version, is_public, config_schema, created_at, updated_at)
                VALUES
                    (:id, :name, :slug, :desc, :output_file, :event, :category, :required,
                     :body_md, '0.1.0', TRUE, '{}', :now, :now)
                ON CONFLICT (slug) DO UPDATE SET
                    name        = EXCLUDED.name,
                    description = EXCLUDED.description,
                    output_file = EXCLUDED.output_file,
                    event       = EXCLUDED.event,
                    category    = EXCLUDED.category,
                    required    = EXCLUDED.required,
                    body_md     = COALESCE(EXCLUDED.body_md, hooks.body_md),
                    updated_at  = EXCLUDED.updated_at
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "slug": slug,
                "desc": desc,
                "output_file": output_file,
                "event": event,
                "category": category,
                "required": required,
                "body_md": body_md,
                "now": _NOW,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    hook_slugs = [slug for slug, *_ in _HOOKS]
    skill_slugs = [slug for slug, *_ in _SKILLS]
    agent_slugs = [slug for slug, *_ in _AGENTS]

    conn.execute(sa.text("DELETE FROM hooks WHERE slug = ANY(:slugs)"), {"slugs": hook_slugs})
    conn.execute(sa.text("DELETE FROM skills WHERE slug = ANY(:slugs)"), {"slugs": skill_slugs})
    conn.execute(sa.text("DELETE FROM agents WHERE slug = ANY(:slugs)"), {"slugs": agent_slugs})
