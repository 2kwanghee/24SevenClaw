"""requirements_svc 단위 테스트 — As-Is 유추, 태그 계산, scenario 재정의, LLM 미설정 fallback."""

from __future__ import annotations

import pytest

from app.config import settings
from app.services.modernize.requirements_svc import (
    build_requirements_artifact,
    derive_as_is_stack,
    derive_scenario_from_tags,
    tag_requirements,
)


@pytest.fixture
def no_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "")


def _stack(
    *,
    runtime: str | None = None,
    runtime_version: str | None = None,
    db_type: str | None = None,
    framework: str | None = None,
    infra: str | None = None,
) -> dict[str, str | None]:
    return {
        "runtime": runtime,
        "runtime_version": runtime_version,
        "db_type": db_type,
        "framework": framework,
        "infra": infra,
    }


def test_derive_as_is_stack_from_framework_signals() -> None:
    stack = derive_as_is_stack(
        lang_distribution={"python": 0.9, "javascript": 0.1},
        framework_signals={"python": "3.8", "django": "3.2"},
        manifests=[{"path": "pyproject.toml", "raw_deps": {"psycopg2": "2.9"}}],
    )
    assert stack["runtime"] == "python"
    assert stack["runtime_version"] == "3.8"
    assert stack["framework"] == "django"
    assert stack["framework_version"] == "3.2"
    assert stack["db_type"] == "postgresql"


def test_derive_as_is_stack_fallback_to_dominant_language() -> None:
    stack = derive_as_is_stack(
        lang_distribution={"go": 0.7, "javascript": 0.3},
        framework_signals={},
        manifests=[],
    )
    assert stack["runtime"] == "go"
    assert stack["framework"] is None
    assert stack["db_type"] is None


def test_tag_requirements_language_migrate() -> None:
    as_is = _stack(runtime="python", runtime_version="3.8")
    to_be = _stack(runtime="go", runtime_version="1.22")
    tags = tag_requirements(as_is=as_is, to_be=to_be, goals_text="")
    assert tags == ["language_migrate"]


def test_tag_requirements_db_migrate() -> None:
    as_is = _stack(runtime="python", runtime_version="3.12", db_type="mysql")
    to_be = _stack(runtime="python", runtime_version="3.12", db_type="postgresql")
    tags = tag_requirements(as_is=as_is, to_be=to_be, goals_text="")
    assert tags == ["db_migrate"]


def test_tag_requirements_versionup_only() -> None:
    as_is = _stack(runtime="python", runtime_version="3.8")
    to_be = _stack(runtime="python", runtime_version="3.12")
    tags = tag_requirements(as_is=as_is, to_be=to_be, goals_text="")
    assert tags == ["versionup"]


def test_tag_requirements_replatform_on_framework_change() -> None:
    as_is = _stack(runtime="python", runtime_version="3.12", framework="flask")
    to_be = _stack(runtime="python", runtime_version="3.12", framework="fastapi")
    tags = tag_requirements(as_is=as_is, to_be=to_be, goals_text="")
    assert tags == ["replatform"]


def test_tag_requirements_defaults_to_refactor_when_no_diff() -> None:
    as_is = _stack(runtime="python", runtime_version="3.12")
    to_be = _stack(runtime="python", runtime_version="3.12")
    tags = tag_requirements(as_is=as_is, to_be=to_be, goals_text="코드 리팩터링이 필요합니다")
    assert tags == ["refactor"]


def test_tag_requirements_priority_ordering_language_migrate_first() -> None:
    as_is = _stack(runtime="python", runtime_version="3.8", db_type="mysql")
    to_be = _stack(runtime="go", runtime_version="1.22", db_type="postgresql")
    tags = tag_requirements(as_is=as_is, to_be=to_be, goals_text="")
    assert tags[0] == "language_migrate"
    assert "db_migrate" in tags


def test_derive_scenario_from_tags_maps_to_existing_three() -> None:
    def derive(tags: list[str], fallback: str) -> str:
        return derive_scenario_from_tags(tags, fallback_scenario=fallback)

    assert derive(["language_migrate"], "versionup") == "language_migrate"
    assert derive(["db_migrate"], "versionup") == "language_migrate"
    assert derive(["replatform"], "versionup") == "language_migrate"
    assert derive(["versionup"], "refactor") == "versionup"
    assert derive(["refactor"], "versionup") == "refactor"


def test_derive_scenario_from_tags_fallback_when_empty() -> None:
    assert derive_scenario_from_tags([], fallback_scenario="versionup") == "versionup"


@pytest.mark.asyncio
async def test_build_requirements_artifact_fallback_without_llm(no_anthropic_key: None) -> None:
    md = await build_requirements_artifact(
        goals_text="MySQL 을 PostgreSQL 로 전환하고 싶습니다",
        as_is_stack={
            "db_type": "mysql",
            "db_version": "5.7",
            "runtime": "python",
            "runtime_version": "3.8",
            "framework": None,
            "framework_version": None,
            "infra": None,
            "extra": {},
        },
        to_be_stack={
            "db_type": "postgresql",
            "db_version": "16",
            "runtime": "python",
            "runtime_version": "3.8",
            "framework": None,
            "framework_version": None,
            "infra": None,
            "extra": {},
        },
        requirement_tags=["db_migrate"],
    )
    assert "mysql" in md.lower()
    assert "postgresql" in md.lower()
    assert "db_migrate" in md
    assert "Anthropic API key" in md
