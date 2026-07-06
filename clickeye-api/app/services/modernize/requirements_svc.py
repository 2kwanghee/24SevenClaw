"""Phase 2 — 현대화 요구사항 분석: AS-IS 스택 유추, 요구사항 태그 계산, metaprompt 정제.

구조화 데이터(as_is/to_be 스택, requirement_tags)는 LLM 없이도 100% 생성 가능해야 한다
(기존 fallback 원칙 유지). LLM 은 사람이 읽는 `requirements.md` 정제에만 사용한다.
계산된 `requirement_tags` 는 이후 에이전트 매핑(CE-291)의 입력이 된다.
"""

from __future__ import annotations

import json
from typing import Any

from app.config import settings
from app.services.claude_service import ClaudeService

# framework_signals 키 → 정규화된 runtime 이름
_RUNTIME_KEYS = {
    "python": "python",
    "node": "node",
    "nodejs": "node",
    "java": "java",
    "go": "go",
    "golang": "go",
    "ruby": "ruby",
    "php": "php",
    "dotnet": "dotnet",
    ".net": "dotnet",
}

_FRAMEWORK_KEYS = {
    "django",
    "flask",
    "fastapi",
    "express",
    "nestjs",
    "next",
    "nextjs",
    "spring",
    "spring-boot",
    "rails",
    "laravel",
    "symfony",
    "gin",
    "echo",
}

# 패키지/의존성 이름 부분 문자열 매칭 → DB 종류
_DB_KEYWORDS = {
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "psycopg": "postgresql",
    "asyncpg": "postgresql",
    "mariadb": "mariadb",
    "mysql": "mysql",
    "pymysql": "mysql",
    "oracle": "oracle",
    "cxoracle": "oracle",
    "oracledb": "oracle",
    "mssql": "mssql",
    "pyodbc": "mssql",
    "pymssql": "mssql",
    "sqlite": "sqlite",
    "mongodb": "mongodb",
    "mongoose": "mongodb",
    "pymongo": "mongodb",
}

# 태그 우선순위 (넓은 영향 범위 → 좁은 영향 범위)
_TAG_PRIORITY = ["language_migrate", "db_migrate", "replatform", "versionup", "refactor"]

# 5종 요구사항 태그 → 기존 파이프라인이 지원하는 3종 scenario 매핑
_TAG_TO_SCENARIO = {
    "language_migrate": "language_migrate",
    "db_migrate": "language_migrate",
    "replatform": "language_migrate",
    "versionup": "versionup",
    "refactor": "refactor",
}

_REFACTOR_KEYWORDS = ("리팩터", "리팩토링", "refactor", "기술부채", "technical debt")


def derive_as_is_stack(
    *,
    lang_distribution: dict[str, float],
    framework_signals: dict[str, Any],
    manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    """CodebaseAnalysis 결과에서 As-Is StackDescriptor 를 최선 추정한다.

    완전한 추정은 불가능 — 미검출 필드는 None 으로 남기고 To-Be 입력 시 사용자가 보정한다.
    """
    runtime: str | None = None
    runtime_version: str | None = None
    for key, val in framework_signals.items():
        normalized = key.lower()
        if normalized in _RUNTIME_KEYS:
            runtime = _RUNTIME_KEYS[normalized]
            runtime_version = str(val)
            break
    if runtime is None and lang_distribution:
        runtime = max(lang_distribution.items(), key=lambda kv: kv[1])[0].lower()

    framework: str | None = None
    framework_version: str | None = None
    for key, val in framework_signals.items():
        if key.lower() in _FRAMEWORK_KEYS:
            framework = key.lower()
            framework_version = str(val)
            break

    candidates: list[str] = list(framework_signals.keys())
    for m in manifests:
        raw_deps = m.get("raw_deps")
        if isinstance(raw_deps, dict):
            candidates.extend(raw_deps.keys())

    db_type: str | None = None
    for cand in candidates:
        normalized = cand.lower().replace("-", "").replace("_", "")
        for keyword, dbtype in _DB_KEYWORDS.items():
            if keyword in normalized:
                db_type = dbtype
                break
        if db_type:
            break

    return {
        "db_type": db_type,
        "db_version": None,
        "runtime": runtime,
        "runtime_version": runtime_version,
        "framework": framework,
        "framework_version": framework_version,
        "infra": None,
        "extra": {},
    }


def tag_requirements(
    *,
    as_is: dict[str, Any],
    to_be: dict[str, Any],
    goals_text: str,
) -> list[str]:
    """As-Is ↔ To-Be 스택 비교 + goals_text 로 요구사항 유형 태그를 산출한다.

    비교 대상 필드가 없으면(감지 실패) 판단을 보류하고, 아무 태그도 성립하지 않으면
    기본값으로 'refactor' 를 부여한다.
    """
    tags: set[str] = set()

    as_runtime = _lower_or_none(as_is.get("runtime"))
    to_runtime = _lower_or_none(to_be.get("runtime"))
    as_db = _lower_or_none(as_is.get("db_type"))
    to_db = _lower_or_none(to_be.get("db_type"))
    as_fw = _lower_or_none(as_is.get("framework"))
    to_fw = _lower_or_none(to_be.get("framework"))
    as_infra = _lower_or_none(as_is.get("infra"))
    to_infra = _lower_or_none(to_be.get("infra"))

    if to_runtime and as_runtime and to_runtime != as_runtime:
        tags.add("language_migrate")
    elif to_runtime and as_runtime and as_is.get("runtime_version") != to_be.get("runtime_version"):
        tags.add("versionup")

    if to_db and as_db and to_db != as_db:
        tags.add("db_migrate")
    elif to_db and as_db and as_is.get("db_version") != to_be.get("db_version"):
        tags.add("versionup")

    if (to_fw and as_fw and to_fw != as_fw) or (to_infra and as_infra and to_infra != as_infra):
        tags.add("replatform")

    lowered_goals = (goals_text or "").lower()
    if any(keyword in lowered_goals for keyword in _REFACTOR_KEYWORDS):
        tags.add("refactor")

    if not tags:
        tags.add("refactor")

    return [tag for tag in _TAG_PRIORITY if tag in tags]


def derive_scenario_from_tags(tags: list[str], *, fallback_scenario: str) -> str:
    """5종 요구사항 태그를 기존 3종 scenario(versionup/refactor/language_migrate) 로 재정의.

    태그가 비어있으면 세션 생성 시 사용자가 선택한 기존 scenario 를 그대로 fallback 한다.
    """
    for tag in _TAG_PRIORITY:
        if tag in tags:
            return _TAG_TO_SCENARIO[tag]
    return fallback_scenario


_REQUIREMENTS_SYSTEM = """You are a senior modernization requirements analyst.

You receive JSON: goals_text, as_is_stack, to_be_stack, requirement_tags.

Produce a concise Markdown requirements brief (<= 500 words) with exactly these sections:
1. **현황 (As-Is)** — summarize as_is_stack
2. **목표 (To-Be)** — summarize to_be_stack, weaving in goals_text
3. **요구사항 유형** — list requirement_tags with a one-line meaning for each
4. **주요 리스크/전제조건**

STRICT: markdown only, no JSON, no code fences. Use Korean if goals_text is Korean,
otherwise English."""


async def build_requirements_artifact(
    *,
    goals_text: str,
    as_is_stack: dict[str, Any],
    to_be_stack: dict[str, Any],
    requirement_tags: list[str],
) -> str:
    """`requirements.md` 본문 생성. Anthropic key 미설정/실패 시 결정론적 markdown fallback."""
    if not settings.anthropic_api_key:
        return _placeholder_requirements_md(
            goals_text=goals_text,
            as_is_stack=as_is_stack,
            to_be_stack=to_be_stack,
            requirement_tags=requirement_tags,
        )

    service = ClaudeService()
    client = service._get_client()  # noqa: SLF001 — claude_service 패턴 재사용
    context = {
        "goals_text": goals_text or "",
        "as_is_stack": as_is_stack,
        "to_be_stack": to_be_stack,
        "requirement_tags": requirement_tags,
    }
    try:
        response = await client.messages.create(
            model=settings.anthropic_model_default,
            max_tokens=1200,
            system=_REQUIREMENTS_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False, indent=2),
                }
            ],
        )
    except Exception:
        return _placeholder_requirements_md(
            goals_text=goals_text,
            as_is_stack=as_is_stack,
            to_be_stack=to_be_stack,
            requirement_tags=requirement_tags,
        )

    md = ""
    for block in response.content:
        if hasattr(block, "text"):
            md += block.text
    return md.strip() or _placeholder_requirements_md(
        goals_text=goals_text,
        as_is_stack=as_is_stack,
        to_be_stack=to_be_stack,
        requirement_tags=requirement_tags,
    )


def _placeholder_requirements_md(
    *,
    goals_text: str,
    as_is_stack: dict[str, Any],
    to_be_stack: dict[str, Any],
    requirement_tags: list[str],
) -> str:
    """LLM 미사용 시 정적 요약 — 구조화 입력만으로 markdown 생성."""

    def _stack_lines(stack: dict[str, Any]) -> list[str]:
        labels = (
            ("DB", "db_type"),
            ("DB 버전", "db_version"),
            ("런타임", "runtime"),
            ("런타임 버전", "runtime_version"),
            ("프레임워크", "framework"),
            ("프레임워크 버전", "framework_version"),
            ("인프라", "infra"),
        )
        lines = [f"- {label}: `{stack[key]}`" for label, key in labels if stack.get(key)]
        return lines or ["- (감지된 정보 없음)"]

    lines = [
        "# 현대화 요구사항 분석 (placeholder)",
        "",
        "## 현황 (As-Is)",
        *_stack_lines(as_is_stack),
        "",
        "## 목표 (To-Be)",
        *_stack_lines(to_be_stack),
        "",
        "## 요구사항 유형",
        *([f"- {tag}" for tag in requirement_tags] or ["- (태그 없음)"]),
    ]
    if goals_text:
        lines.extend(["", "## 사용자 목표", goals_text])
    lines.extend(
        [
            "",
            "## 안내",
            "이 요약은 Anthropic API key 미설정 시 표시되는 정적 요약입니다.",
            "key 설정 후 재생성 시 AI 가 문맥에 맞는 요구사항 브리프를 작성합니다.",
        ]
    )
    return "\n".join(lines)


def _lower_or_none(value: Any) -> str | None:
    return value.lower() if isinstance(value, str) and value else None
