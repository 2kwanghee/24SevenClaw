"""plan_builder 순수 함수 단위 테스트 (Phase 4 — 태스크 DAG/웨이브)."""

from __future__ import annotations

import pytest

from app.services.modernize import plan_builder

pytestmark = pytest.mark.no_db


def _rec(category: str, target_path: str | None = None, title: str = "t") -> dict:
    return {"category": category, "target_path": target_path, "title": title}


def test_build_plan_orders_migrate_before_refactor_before_remove() -> None:
    recs = [
        _rec("remove", title="cleanup"),
        _rec("migrate", title="schema"),
        _rec("refactor", title="tidy"),
    ]
    plan = plan_builder.build_plan(recs)

    # idx 0=remove, 1=migrate, 2=refactor. wave(migrate) < wave(refactor) < wave(remove)
    assert plan[1]["wave"] < plan[2]["wave"] < plan[0]["wave"]


def test_same_target_path_chains_sequentially() -> None:
    recs = [
        _rec("upgrade", target_path="pyproject.toml", title="a"),
        _rec("upgrade", target_path="pyproject.toml", title="b"),
        _rec("upgrade", target_path="pyproject.toml", title="c"),
    ]
    plan = plan_builder.build_plan(recs)

    assert plan[1]["depends_on"] == [0]
    assert plan[2]["depends_on"] == [1]
    assert plan[0]["wave"] == 0
    assert plan[1]["wave"] == 1
    assert plan[2]["wave"] == 2


def test_compute_waves_detects_cycle() -> None:
    with pytest.raises(plan_builder.PlanValidationError):
        plan_builder.compute_waves([[1], [0]])


def test_compute_waves_rejects_out_of_range_dependency() -> None:
    with pytest.raises(plan_builder.PlanValidationError):
        plan_builder.compute_waves([[5]])


def test_infer_agent_by_target_path_prefix() -> None:
    assert plan_builder.infer_agent("clickeye-web/src/app.tsx", "refactor") == "web"
    assert plan_builder.infer_agent("clickeye-api/app/main.py", "upgrade") == "api"
    assert plan_builder.infer_agent("clickeye-infra/docker-compose.yml", "migrate") == "infra"
    assert plan_builder.infer_agent(None, "upgrade") == "fullstack"
    assert plan_builder.infer_agent("unknown/path.txt", "upgrade") == "fullstack"


def test_build_plan_json_groups_by_wave() -> None:
    recs = [
        {
            "id": "r0",
            "idx": 0,
            "title": "schema",
            "category": "migrate",
            "effort": "M",
            "risk": "high",
            "assigned_agent": "api",
            "depends_on": [],
            "wave": 0,
        },
        {
            "id": "r1",
            "idx": 1,
            "title": "app code",
            "category": "refactor",
            "effort": "M",
            "risk": "med",
            "assigned_agent": "api",
            "depends_on": [0],
            "wave": 1,
        },
    ]
    plan_json = plan_builder.build_plan_json(session_id="s1", recs=recs)

    assert plan_json["session_id"] == "s1"
    assert [w["wave"] for w in plan_json["waves"]] == [0, 1]
    assert plan_json["waves"][1]["tasks"][0]["depends_on"] == [0]


def test_render_plan_markdown_lists_waves_and_dependencies() -> None:
    recs = [
        {
            "idx": 0,
            "title": "schema",
            "wave": 0,
            "depends_on": [],
            "assigned_agent": "api",
            "effort": "M",
            "risk": "high",
        },
        {
            "idx": 1,
            "title": "app code",
            "wave": 1,
            "depends_on": [0],
            "assigned_agent": "api",
            "effort": "M",
            "risk": "med",
        },
    ]
    md = plan_builder.render_plan_markdown(recs)

    assert "## Wave 0" in md
    assert "## Wave 1" in md
    assert "선행: #0" in md


def test_render_plan_markdown_empty_recs() -> None:
    md = plan_builder.render_plan_markdown([])
    assert "권장안이 없어" in md


# ── build_orchestrator_plan (plan.json 실행 계약, CE-290 orchestrator 입력) ──
_ORCH_KWARGS = {
    "session_id": "session-uuid-123",
    "repo_full_name": "acme/api",
    "scenario": "versionup",
}


def test_orch_plan_has_required_top_level_fields() -> None:
    plan = plan_builder.build_orchestrator_plan(recommendations=[], **_ORCH_KWARGS)
    assert plan["version"] == 1
    assert plan["session_id"] == "session-uuid-123"
    assert plan["repo_full_name"] == "acme/api"
    assert plan["scenario"] == "versionup"
    assert plan["tasks"] == []


def test_orch_independent_tasks_have_no_dependencies() -> None:
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
    plan = plan_builder.build_orchestrator_plan(recommendations=recs, **_ORCH_KWARGS)
    by_id = {t["id"]: t for t in plan["tasks"]}
    assert by_id["CE-101"]["depends_on"] == []
    assert by_id["CE-102"]["depends_on"] == []


def test_orch_same_target_path_creates_conflict_dependency() -> None:
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
    plan = plan_builder.build_orchestrator_plan(recommendations=recs, **_ORCH_KWARGS)
    by_id = {t["id"]: t for t in plan["tasks"]}
    assert by_id["CE-1"]["depends_on"] == []
    assert by_id["CE-2"]["depends_on"] == ["CE-1"]


def test_orch_migrate_category_chains_by_priority() -> None:
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
    plan = plan_builder.build_orchestrator_plan(recommendations=recs, **_ORCH_KWARGS)
    by_id = {t["id"]: t for t in plan["tasks"]}
    assert by_id["CE-M1"]["depends_on"] == []
    assert by_id["CE-M2"]["depends_on"] == ["CE-M1"]
    assert by_id["CE-M3"]["depends_on"] == ["CE-M2"]


def test_orch_task_prompt_file_and_gate_are_derived() -> None:
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
    plan = plan_builder.build_orchestrator_plan(recommendations=recs, **_ORCH_KWARGS)
    task = plan["tasks"][0]
    assert task["prompt_file"] == ".ralph/tasks/CE-101.md"
    assert task["gate"]["test_cmd"] is not None
    assert task["risk"] == "high"


def test_orch_task_id_falls_back_to_rec_id_when_no_linear_identifier() -> None:
    recs = [{"id": "rec-uuid-1", "title": "no linear id yet", "priority": 5}]
    plan = plan_builder.build_orchestrator_plan(recommendations=recs, **_ORCH_KWARGS)
    assert plan["tasks"][0]["id"] == "rec-uuid-1"


def test_orch_unknown_target_path_has_no_gate_commands() -> None:
    recs = [{"linear_identifier": "CE-1", "title": "misc", "target_path": "README.md"}]
    plan = plan_builder.build_orchestrator_plan(recommendations=recs, **_ORCH_KWARGS)
    gate = plan["tasks"][0]["gate"]
    assert gate == {"test_cmd": None, "lint_cmd": None}
