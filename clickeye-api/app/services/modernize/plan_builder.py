"""Step 8 — `plan.json` 빌드: 권장안(recommendations) → 태스크 DAG.

ZIP 에 포함되는 `scripts/orchestrator.py` 가 읽는 실행 계획서. 각 태스크는
`.ralph/tasks/<identifier>.md` 프롬프트 파일을 가리키며, `depends_on` 으로 실행 순서를
표현한다 (웨이브 계산은 orchestrator.py 가 위상정렬로 런타임에 수행 — 여기서는 저장하지 않음).

의존성 생성 규칙:
    1. category == 'migrate' 인 태스크들은 priority 오름차순으로 체인 의존
       (scaffolding → ... → cutover 순서 보장).
    2. 동일 target_path 를 다루는 태스크는 동시 편집 충돌을 피하기 위해
       priority 가 낮은(먼저 실행되는) 태스크에 의존.
    3. 그 외에는 독립 태스크 (depends_on = []).
"""

from __future__ import annotations

import re
from typing import Any

_GATE_BY_TARGET: tuple[tuple[str, dict[str, str | None]], ...] = (
    (
        "pyproject.toml",
        {"test_cmd": "uv run pytest --tb=short -q", "lint_cmd": "uv run ruff check ."},
    ),
    ("requirements.txt", {"test_cmd": "pytest --tb=short -q", "lint_cmd": None}),
    ("package.json", {"test_cmd": "npm test", "lint_cmd": "npm run lint"}),
    ("go.mod", {"test_cmd": "go test ./...", "lint_cmd": None}),
    ("cargo.toml", {"test_cmd": "cargo test", "lint_cmd": None}),
)


def build_plan(
    *,
    session_id: str,
    repo_full_name: str,
    scenario: str,
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """recommendations → plan.json 직렬화 가능 dict.

    각 rec 는 zip_builder 와 동일한 필드(id/linear_identifier/title/target_path/risk/
    effort/category/priority)를 사용. 누락 필드는 안전 기본값으로 채운다.
    """
    tasks: list[dict[str, Any]] = []
    ordered = sorted(recommendations, key=lambda r: _safe_priority(r.get("priority")))

    # target_path 별 첫 등장(가장 낮은 priority) 태스크 id 추적 — 충돌 의존성 생성용
    first_task_by_target: dict[str, str] = {}
    migrate_chain_prev: str | None = None

    for rec in ordered:
        task_id = _resolve_task_id(rec)
        target_path = str(rec.get("target_path") or "")
        category = str(rec.get("category") or "upgrade")

        depends_on: list[str] = []

        if category == "migrate" and migrate_chain_prev is not None:
            depends_on.append(migrate_chain_prev)
        elif target_path and target_path in first_task_by_target:
            depends_on.append(first_task_by_target[target_path])

        tasks.append(
            {
                "id": task_id,
                "title": str(rec.get("title") or task_id),
                "prompt_file": f".ralph/tasks/{_safe_filename(task_id)}.md",
                "category": category,
                "risk": _normalize_risk(rec.get("risk")),
                "effort": str(rec.get("effort") or "M"),
                "depends_on": depends_on,
                "gate": _resolve_gate(target_path),
            }
        )

        if target_path and target_path not in first_task_by_target:
            first_task_by_target[target_path] = task_id
        if category == "migrate":
            migrate_chain_prev = task_id

    return {
        "version": 1,
        "session_id": session_id,
        "repo_full_name": repo_full_name,
        "scenario": scenario,
        "tasks": tasks,
    }


def _resolve_task_id(rec: dict[str, Any]) -> str:
    identifier = rec.get("linear_identifier") or rec.get("id")
    return str(identifier) if identifier else "unknown"


def _safe_filename(identifier: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", identifier)


def _safe_priority(v: object) -> int:
    if isinstance(v, bool):
        return 50
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    return 50


def _normalize_risk(v: object) -> str:
    if isinstance(v, str) and v.lower() in ("low", "med", "high"):
        return v.lower()
    return "med"


def _resolve_gate(target_path: str) -> dict[str, str | None]:
    lowered = target_path.lower()
    for suffix, gate in _GATE_BY_TARGET:
        if lowered.endswith(suffix):
            return dict(gate)
    return {"test_cmd": None, "lint_cmd": None}
