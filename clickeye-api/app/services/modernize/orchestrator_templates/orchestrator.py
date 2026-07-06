#!/usr/bin/env python3
"""ClickEye Modernize 오케스트레이터.

`plan.json` 의 태스크 DAG(`depends_on`)를 위상정렬하여 웨이브 단위로 순차 실행한다.
각 태스크는 지정된 AI 에이전트 CLI(기본: `claude`)를 호출해 `.ralph/tasks/<id>.md`
프롬프트로 작업을 수행시키고, `gate`(test/lint 커맨드)로 완료를 판정한다. 게이트
실패 시 이전 실패 로그를 프롬프트에 덧붙여 최대 `MAX_GATE_RETRIES` 회까지 재시도한다.

진행 상태는 `.clickeye/state.json` 에 기록되어 중단 후 `--resume` 재개를 지원한다.

Usage:
    python3 scripts/orchestrator.py                  # 전체 실행
    python3 scripts/orchestrator.py --dry-run         # 호출 없이 실행 순서만 출력
    python3 scripts/orchestrator.py --resume          # 중단 지점부터 재개 (완료 태스크 skip)
    python3 scripts/orchestrator.py --only CE-101     # 단일 태스크만 실행
    python3 scripts/orchestrator.py --wave 2          # 특정 웨이브만 실행
"""

from __future__ import annotations

import argparse
import contextlib
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

MAX_GATE_RETRIES = 5
DEFAULT_PLAN_PATH = Path("plan.json")
DEFAULT_STATE_PATH = Path(".clickeye/state.json")


class PlanError(Exception):
    """plan.json 구조 오류 (누락 필드, 순환 의존성, 알 수 없는 태스크 참조 등)."""


def load_plan(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PlanError(f"plan.json 을 찾을 수 없습니다: {path}")
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    tasks = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(tasks, list):
        raise PlanError("plan.json.tasks 가 list 형식이 아닙니다.")
    return dict(data)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"completed": [], "failed": []}
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"completed": [], "failed": []}
    if not isinstance(data, dict):
        return {"completed": [], "failed": []}
    data.setdefault("completed", [])
    data.setdefault("failed", [])
    return dict(data)


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def compute_waves(tasks: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Kahn 알고리즘으로 위상정렬 + 웨이브(의존성 레벨) 계산.

    순환 의존성이거나 존재하지 않는 태스크를 참조하면 PlanError 를 던진다.
    """
    by_id: dict[str, dict[str, Any]] = {t["id"]: t for t in tasks}
    indegree: dict[str, int] = {t["id"]: 0 for t in tasks}
    dependents: dict[str, list[str]] = {t["id"]: [] for t in tasks}

    for t in tasks:
        for dep in t.get("depends_on", []):
            if dep not in by_id:
                raise PlanError(
                    f"태스크 '{t['id']}' 의 depends_on '{dep}' 이 plan.json 에 없습니다."
                )
            indegree[t["id"]] += 1
            dependents[dep].append(t["id"])

    waves: list[list[dict[str, Any]]] = []
    remaining = dict(indegree)
    resolved: set[str] = set()

    while len(resolved) < len(tasks):
        current_wave_ids = sorted(
            tid for tid, deg in remaining.items() if deg == 0 and tid not in resolved
        )
        if not current_wave_ids:
            unresolved = sorted(set(remaining) - resolved)
            raise PlanError(f"순환 의존성 감지: {unresolved}")
        waves.append([by_id[tid] for tid in current_wave_ids])
        for tid in current_wave_ids:
            resolved.add(tid)
            for dependent in dependents[tid]:
                remaining[dependent] -= 1

    return waves


def is_risky(task: dict[str, Any]) -> bool:
    return str(task.get("risk", "")).lower() == "high"


def confirm_risky(
    task: dict[str, Any],
    *,
    assume_yes: bool,
    input_fn: Callable[[str], str] | None = None,
) -> bool:
    """HIGH risk 태스크 실행 전 y/N 확인. assume_yes=True 면 프롬프트 없이 승인.

    `input_fn` 미지정 시 매 호출마다 내장 `input` 을 새로 조회한다 (모듈 로드 시점에
    고정 바인딩하지 않음 — 테스트에서 `builtins.input` 을 monkeypatch 할 수 있도록).
    """
    if not is_risky(task):
        return True
    if assume_yes:
        return True
    prompt_fn = input_fn if input_fn is not None else input
    answer = prompt_fn(
        f"⚠️  [{task['id']}] {task.get('title', '')} 은(는) HIGH risk 태스크입니다. "
        "실행할까요? [y/N] "
    )
    return answer.strip().lower() in ("y", "yes")


def invoke_agent(
    *,
    cli: str,
    task: dict[str, Any],
    workspace: Path,
    attempt: int,
    feedback: str | None,
) -> subprocess.CompletedProcess[str]:
    """에이전트 CLI 호출. 재시도 시 이전 게이트 실패 로그를 프롬프트에 덧붙인다."""
    prompt_path = workspace / str(task["prompt_file"])
    prompt = (
        prompt_path.read_text(encoding="utf-8")
        if prompt_path.exists()
        else str(task.get("title", ""))
    )
    if feedback:
        prompt = f"{prompt}\n\n## 이전 시도 실패 로그 (attempt {attempt})\n```\n{feedback}\n```\n"
    return subprocess.run(
        [cli, "-p", prompt],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def run_gate(task: dict[str, Any], *, workspace: Path) -> tuple[bool, str]:
    """task.gate 의 test_cmd/lint_cmd 실행. 둘 다 미설정이면 검증 없이 통과 처리."""
    gate = task.get("gate") or {}
    test_cmd = gate.get("test_cmd")
    lint_cmd = gate.get("lint_cmd")
    if not test_cmd and not lint_cmd:
        return True, "(게이트 미설정 — 검증 없이 통과 처리)"

    output_parts: list[str] = []
    for cmd in (test_cmd, lint_cmd):
        if not cmd:
            continue
        result = subprocess.run(
            cmd, shell=True, cwd=workspace, capture_output=True, text=True, check=False
        )
        output_parts.append(f"$ {cmd}\n{result.stdout}\n{result.stderr}")
        if result.returncode != 0:
            return False, "\n".join(output_parts)
    return True, "\n".join(output_parts)


InvokeFn = Callable[..., subprocess.CompletedProcess[str]]
GateFn = Callable[..., tuple[bool, str]]


def run_task(
    task: dict[str, Any],
    *,
    workspace: Path,
    cli: str,
    dry_run: bool,
    invoke_fn: InvokeFn = invoke_agent,
    gate_fn: GateFn = run_gate,
) -> bool:
    """단일 태스크 실행: invoke → gate → 실패 시 MAX_GATE_RETRIES 까지 재시도."""
    if dry_run:
        print(f"[DRY-RUN] {task['id']}: {task.get('title', '')} (cli={cli})")
        return True

    feedback: str | None = None
    for attempt in range(1, MAX_GATE_RETRIES + 1):
        print(f"[{task['id']}] attempt {attempt}/{MAX_GATE_RETRIES} — 에이전트 호출 중...")
        invoke_fn(cli=cli, task=task, workspace=workspace, attempt=attempt, feedback=feedback)
        ok, output = gate_fn(task, workspace=workspace)
        if ok:
            print(f"[{task['id']}] 게이트 통과")
            return True
        print(f"[{task['id']}] 게이트 실패 (attempt {attempt}/{MAX_GATE_RETRIES})")
        feedback = output

    print(f"[{task['id']}] 최대 재시도 초과 — 실패 처리")
    return False


def record_work(task: dict[str, Any], *, status: str, workspace: Path) -> None:
    """CE-293 work-recorder 훅 연동 지점. `scripts/work_recorder.py` 가 없으면 조용히 skip."""
    recorder = workspace / "scripts" / "work_recorder.py"
    if not recorder.exists():
        return
    with contextlib.suppress(OSError):
        subprocess.run(
            [sys.executable, str(recorder), "--task-id", str(task["id"]), "--status", status],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
        )


def filter_tasks(
    waves: list[list[dict[str, Any]]], *, only: str | None, wave: int | None
) -> list[list[dict[str, Any]]]:
    if only is not None:
        for w in waves:
            for t in w:
                if t["id"] == only:
                    return [[t]]
        raise PlanError(f"--only '{only}' 태스크를 plan.json 에서 찾을 수 없습니다.")
    if wave is not None:
        idx = wave - 1
        if idx < 0 or idx >= len(waves):
            raise PlanError(f"--wave {wave} 는 범위를 벗어났습니다 (총 {len(waves)}개 웨이브).")
        return [waves[idx]]
    return waves


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ClickEye Modernize 오케스트레이터")
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN_PATH, help="plan.json 경로")
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE_PATH, help="state 파일 경로")
    parser.add_argument("--workspace", type=Path, default=Path("."), help="실행 워크스페이스 루트")
    parser.add_argument("--cli", default="claude", help="AI 에이전트 CLI 실행 파일 (기본: claude)")
    parser.add_argument("--dry-run", action="store_true", help="호출 없이 실행 순서만 출력")
    parser.add_argument(
        "--resume", action="store_true", help="state 파일 기준으로 완료된 태스크는 skip"
    )
    parser.add_argument("--only", metavar="TASK_ID", help="지정한 태스크 1건만 실행")
    parser.add_argument("--wave", type=int, help="지정한 웨이브(1-base)만 실행")
    parser.add_argument(
        "--yes", action="store_true", help="HIGH risk 태스크 확인 프롬프트를 자동 승인"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    try:
        plan = load_plan(args.plan)
        waves = compute_waves(plan["tasks"])
        target_waves = filter_tasks(waves, only=args.only, wave=args.wave)
    except PlanError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    state = load_state(args.state) if args.resume else {"completed": [], "failed": []}
    completed: set[str] = set(state["completed"])

    exit_code = 0
    for wave_idx, wave in enumerate(target_waves, start=1):
        print(f"=== Wave {wave_idx}/{len(target_waves)} ({len(wave)} tasks) ===")
        for task in wave:
            task_id = str(task["id"])
            if task_id in completed:
                print(f"[{task_id}] 이미 완료됨 (resume) — skip")
                continue
            if not confirm_risky(task, assume_yes=args.yes):
                print(f"[{task_id}] 사용자가 거부 — skip")
                continue

            ok = run_task(task, workspace=args.workspace, cli=args.cli, dry_run=args.dry_run)
            if args.dry_run:
                continue

            record_work(task, status="completed" if ok else "failed", workspace=args.workspace)
            if ok:
                completed.add(task_id)
                state["completed"] = sorted(completed)
            else:
                if task_id not in state["failed"]:
                    state["failed"].append(task_id)
                exit_code = 1
            save_state(args.state, state)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
