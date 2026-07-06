"""plan_builder.build_plan 단위 테스트 — 태스크 DAG 의존성 생성 규칙 검증."""

from __future__ import annotations

from typing import Any

from app.services.modernize.plan_builder import build_plan

_BASE_KWARGS: dict[str, Any] = {
    "session_id": "session-uuid-123",
    "repo_full_name": "acme/api",
    "scenario": "versionup",
}


def test_plan_has_required_top_level_fields() -> None:
    plan = build_plan(recommendations=[], **_BASE_KWARGS)
    assert plan["version"] == 1
    assert plan["session_id"] == "session-uuid-123"
    assert plan["repo_full_name"] == "acme/api"
    assert plan["scenario"] == "versionup"
    assert plan["tasks"] == []


def test_independent_tasks_have_no_dependencies() -> None:
    recs = [
        {
            "linear_identifier": "CE-101",
            "title": "Django upgrade",
            "target_path": "pyproject.toml",
            "risk": "high",
            "category": "upgrade",
            "priority": 10,
        },
        {
            "linear_identifier": "CE-102",
            "title": "React upgrade",
            "target_path": "package.json",
            "risk": "low",
            "category": "upgrade",
            "priority": 20,
        },
    ]
    plan = build_plan(recommendations=recs, **_BASE_KWARGS)
    by_id = {t["id"]: t for t in plan["tasks"]}
    assert by_id["CE-101"]["depends_on"] == []
    assert by_id["CE-102"]["depends_on"] == []


def test_same_target_path_creates_conflict_dependency() -> None:
    """동일 target_path 를 다루는 두 태스크는 priority 낮은(먼저) 쪽에 의존."""
    recs = [
        {
            "linear_identifier": "CE-1",
            "title": "first edit",
            "target_path": "pyproject.toml",
            "category": "upgrade",
            "priority": 5,
        },
        {
            "linear_identifier": "CE-2",
            "title": "second edit",
            "target_path": "pyproject.toml",
            "category": "upgrade",
            "priority": 15,
        },
    ]
    plan = build_plan(recommendations=recs, **_BASE_KWARGS)
    by_id = {t["id"]: t for t in plan["tasks"]}
    assert by_id["CE-1"]["depends_on"] == []
    assert by_id["CE-2"]["depends_on"] == ["CE-1"]


def test_migrate_category_chains_by_priority() -> None:
    """category=migrate 태스크는 priority 오름차순으로 체인 의존 (scaffolding → cutover)."""
    recs = [
        {"linear_identifier": "CE-M3", "title": "cutover", "category": "migrate", "priority": 30},
        {
            "linear_identifier": "CE-M1",
            "title": "scaffolding",
            "category": "migrate",
            "priority": 10,
        },
        {
            "linear_identifier": "CE-M2",
            "title": "migrate core",
            "category": "migrate",
            "priority": 20,
        },
    ]
    plan = build_plan(recommendations=recs, **_BASE_KWARGS)
    by_id = {t["id"]: t for t in plan["tasks"]}
    assert by_id["CE-M1"]["depends_on"] == []
    assert by_id["CE-M2"]["depends_on"] == ["CE-M1"]
    assert by_id["CE-M3"]["depends_on"] == ["CE-M2"]


def test_task_prompt_file_and_gate_are_derived() -> None:
    recs = [
        {
            "linear_identifier": "CE-101",
            "title": "Django upgrade",
            "target_path": "pyproject.toml",
            "risk": "high",
            "category": "upgrade",
            "priority": 10,
        }
    ]
    plan = build_plan(recommendations=recs, **_BASE_KWARGS)
    task = plan["tasks"][0]
    assert task["prompt_file"] == ".ralph/tasks/CE-101.md"
    assert task["gate"]["test_cmd"] is not None
    assert task["risk"] == "high"


def test_task_id_falls_back_to_rec_id_when_no_linear_identifier() -> None:
    recs = [{"id": "rec-uuid-1", "title": "no linear id yet", "priority": 5}]
    plan = build_plan(recommendations=recs, **_BASE_KWARGS)
    assert plan["tasks"][0]["id"] == "rec-uuid-1"


def test_unknown_target_path_has_no_gate_commands() -> None:
    recs = [{"linear_identifier": "CE-1", "title": "misc", "target_path": "README.md"}]
    plan = build_plan(recommendations=recs, **_BASE_KWARGS)
    gate = plan["tasks"][0]["gate"]
    assert gate == {"test_cmd": None, "lint_cmd": None}


def test_assigned_agent_is_none_without_requirement_tags() -> None:
    """requirement_tags 미지정 시 기존 동작 유지 — assigned_agent 는 항상 None."""
    recs = [{"linear_identifier": "CE-M1", "title": "migrate step", "category": "migrate"}]
    plan = build_plan(recommendations=recs, **_BASE_KWARGS)
    assert plan["requirement_tags"] == []
    assert plan["tasks"][0]["assigned_agent"] is None


def test_assigned_agent_set_for_migrate_task_with_db_migrate_tag() -> None:
    recs = [
        {"linear_identifier": "CE-M1", "title": "schema dump", "category": "migrate"},
        {"linear_identifier": "CE-U1", "title": "unrelated upgrade", "category": "upgrade"},
    ]
    plan = build_plan(
        recommendations=recs,
        requirement_tags=["db_migrate"],
        source_db="mariadb",
        target_db="postgresql",
        **_BASE_KWARGS,
    )
    assert plan["requirement_tags"] == ["db_migrate"]
    by_id = {t["id"]: t for t in plan["tasks"]}
    assert by_id["CE-M1"]["assigned_agent"] == "db-migrator"
    # migrate 가 아닌 카테고리는 여전히 배정하지 않음(MVP 범위)
    assert by_id["CE-U1"]["assigned_agent"] is None
