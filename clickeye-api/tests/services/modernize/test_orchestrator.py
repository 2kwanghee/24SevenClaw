"""orchestrator.py 단위 테스트 — dry-run / resume / 게이트 실패 재시도 시나리오.

`scripts/orchestrator.py` 는 customer 로컬 환경에서 stdlib 만으로 동작하는 독립
스크립트지만, ZIP 생성 이전 원본은 `orchestrator_templates` 패키지에 있으므로
직접 import 해서 검증한다. 모든 실제 프로세스 호출은 `subprocess.run` 을
monkeypatch 하여 대체한다.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from app.services.modernize.orchestrator_templates import orchestrator


def _write_plan(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "session_id": "s1",
                "repo_full_name": "acme/api",
                "scenario": "versionup",
                "tasks": tasks,
            }
        ),
        encoding="utf-8",
    )


def _completed(
    returncode: int = 0, stdout: str = "", stderr: str = ""
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class TestComputeWaves:
    def test_independent_tasks_form_single_wave(self) -> None:
        tasks: list[dict[str, Any]] = [
            {"id": "A", "depends_on": []},
            {"id": "B", "depends_on": []},
        ]
        waves = orchestrator.compute_waves(tasks)
        assert len(waves) == 1
        assert {t["id"] for t in waves[0]} == {"A", "B"}

    def test_dependency_creates_two_waves(self) -> None:
        tasks: list[dict[str, Any]] = [
            {"id": "A", "depends_on": []},
            {"id": "B", "depends_on": ["A"]},
        ]
        waves = orchestrator.compute_waves(tasks)
        assert [t["id"] for t in waves[0]] == ["A"]
        assert [t["id"] for t in waves[1]] == ["B"]

    def test_cycle_raises_plan_error(self) -> None:
        tasks: list[dict[str, Any]] = [
            {"id": "A", "depends_on": ["B"]},
            {"id": "B", "depends_on": ["A"]},
        ]
        with pytest.raises(orchestrator.PlanError):
            orchestrator.compute_waves(tasks)

    def test_unknown_dependency_raises_plan_error(self) -> None:
        tasks: list[dict[str, Any]] = [{"id": "A", "depends_on": ["ghost"]}]
        with pytest.raises(orchestrator.PlanError):
            orchestrator.compute_waves(tasks)


def test_dry_run_does_not_invoke_subprocess_or_touch_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    _write_plan(
        plan_path,
        [
            {
                "id": "CE-1",
                "title": "t1",
                "prompt_file": ".ralph/tasks/CE-1.md",
                "risk": "low",
                "depends_on": [],
                "gate": {},
            },
            {
                "id": "CE-2",
                "title": "t2",
                "prompt_file": ".ralph/tasks/CE-2.md",
                "risk": "low",
                "depends_on": [],
                "gate": {},
            },
        ],
    )

    calls: list[Any] = []
    monkeypatch.setattr(
        orchestrator.subprocess, "run", lambda *a, **k: calls.append((a, k)) or _completed()
    )

    exit_code = orchestrator.main(
        [
            "--plan",
            str(plan_path),
            "--state",
            str(state_path),
            "--workspace",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert calls == []
    assert not state_path.exists()


def test_resume_skips_already_completed_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    _write_plan(
        plan_path,
        [
            {
                "id": "CE-1",
                "title": "t1",
                "prompt_file": ".ralph/tasks/CE-1.md",
                "risk": "low",
                "depends_on": [],
                "gate": {},
            },
            {
                "id": "CE-2",
                "title": "t2",
                "prompt_file": ".ralph/tasks/CE-2.md",
                "risk": "low",
                "depends_on": ["CE-1"],
                "gate": {},
            },
        ],
    )
    state_path.parent.mkdir(parents=True)
    state_path.write_text(json.dumps({"completed": ["CE-1"], "failed": []}), encoding="utf-8")

    invoke_count = {"n": 0}

    def fake_run(cmd: Any, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if isinstance(cmd, list):
            invoke_count["n"] += 1
        return _completed()

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    exit_code = orchestrator.main(
        [
            "--plan",
            str(plan_path),
            "--state",
            str(state_path),
            "--workspace",
            str(tmp_path),
            "--resume",
            "--yes",
        ]
    )

    assert exit_code == 0
    # CE-1 은 resume 으로 skip — 에이전트는 CE-2 에 대해서만 1번 호출됨
    assert invoke_count["n"] == 1
    final_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert set(final_state["completed"]) == {"CE-1", "CE-2"}


def test_gate_failure_retries_then_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    _write_plan(
        plan_path,
        [
            {
                "id": "CE-1",
                "title": "t1",
                "prompt_file": ".ralph/tasks/CE-1.md",
                "risk": "low",
                "depends_on": [],
                "gate": {"test_cmd": "pytest", "lint_cmd": None},
            }
        ],
    )

    gate_calls = {"n": 0}

    def fake_run(cmd: Any, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if isinstance(cmd, str):
            gate_calls["n"] += 1
            # 처음 2번은 실패, 3번째부터 성공
            return _completed(returncode=0 if gate_calls["n"] >= 3 else 1, stderr="gate failed")
        return _completed()

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    exit_code = orchestrator.main(
        [
            "--plan",
            str(plan_path),
            "--state",
            str(state_path),
            "--workspace",
            str(tmp_path),
            "--yes",
        ]
    )

    assert exit_code == 0
    assert gate_calls["n"] == 3
    final_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert final_state["completed"] == ["CE-1"]
    assert final_state["failed"] == []


def test_gate_failure_exhausts_retries_and_marks_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    _write_plan(
        plan_path,
        [
            {
                "id": "CE-1",
                "title": "t1",
                "prompt_file": ".ralph/tasks/CE-1.md",
                "risk": "low",
                "depends_on": [],
                "gate": {"test_cmd": "pytest", "lint_cmd": None},
            }
        ],
    )

    gate_calls = {"n": 0}

    def fake_run(cmd: Any, *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if isinstance(cmd, str):
            gate_calls["n"] += 1
            return _completed(returncode=1, stderr="always fails")
        return _completed()

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    exit_code = orchestrator.main(
        [
            "--plan",
            str(plan_path),
            "--state",
            str(state_path),
            "--workspace",
            str(tmp_path),
            "--yes",
        ]
    )

    assert exit_code == 1
    assert gate_calls["n"] == orchestrator.MAX_GATE_RETRIES
    final_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert final_state["failed"] == ["CE-1"]
    assert final_state["completed"] == []


def test_high_risk_task_skipped_when_user_declines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    _write_plan(
        plan_path,
        [
            {
                "id": "CE-1",
                "title": "risky change",
                "prompt_file": ".ralph/tasks/CE-1.md",
                "risk": "high",
                "depends_on": [],
                "gate": {},
            }
        ],
    )

    calls: list[Any] = []
    monkeypatch.setattr(
        orchestrator.subprocess, "run", lambda *a, **k: calls.append(1) or _completed()
    )
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "n")

    exit_code = orchestrator.main(
        ["--plan", str(plan_path), "--state", str(state_path), "--workspace", str(tmp_path)]
    )

    assert exit_code == 0
    assert calls == []  # 사용자가 거부 → 에이전트 호출 없음


def test_high_risk_task_runs_when_user_confirms(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    _write_plan(
        plan_path,
        [
            {
                "id": "CE-1",
                "title": "risky change",
                "prompt_file": ".ralph/tasks/CE-1.md",
                "risk": "high",
                "depends_on": [],
                "gate": {},
            }
        ],
    )

    calls: list[Any] = []
    monkeypatch.setattr(
        orchestrator.subprocess, "run", lambda *a, **k: calls.append(1) or _completed()
    )
    monkeypatch.setattr("builtins.input", lambda *_a, **_k: "y")

    exit_code = orchestrator.main(
        ["--plan", str(plan_path), "--state", str(state_path), "--workspace", str(tmp_path)]
    )

    assert exit_code == 0
    assert len(calls) == 1
    final_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert final_state["completed"] == ["CE-1"]


def test_only_filters_to_single_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    task_kwargs = {"prompt_file": "x", "risk": "low", "depends_on": [], "gate": {}}
    _write_plan(
        plan_path,
        [
            {"id": "CE-1", "title": "t1", **task_kwargs},
            {"id": "CE-2", "title": "t2", **task_kwargs},
        ],
    )
    monkeypatch.setattr(orchestrator.subprocess, "run", lambda *a, **k: _completed())

    exit_code = orchestrator.main(
        [
            "--plan",
            str(plan_path),
            "--state",
            str(state_path),
            "--workspace",
            str(tmp_path),
            "--only",
            "CE-2",
            "--yes",
        ]
    )

    assert exit_code == 0
    final_state = json.loads(state_path.read_text(encoding="utf-8"))
    assert final_state["completed"] == ["CE-2"]


def test_unknown_only_task_returns_error_exit_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "plan.json"
    state_path = tmp_path / ".clickeye" / "state.json"
    _write_plan(
        plan_path,
        [
            {
                "id": "CE-1",
                "title": "t1",
                "prompt_file": "x",
                "risk": "low",
                "depends_on": [],
                "gate": {},
            }
        ],
    )
    monkeypatch.setattr(orchestrator.subprocess, "run", lambda *a, **k: _completed())

    exit_code = orchestrator.main(
        [
            "--plan",
            str(plan_path),
            "--state",
            str(state_path),
            "--workspace",
            str(tmp_path),
            "--only",
            "CE-999",
        ]
    )

    assert exit_code == 1
