"""Phase 4 — 권장안(Recommendation) 리스트를 실행 계획 DAG 로 격상.

순수 함수 모음 (DB/네트워크 접근 없음). 갭 매트릭스(category) 순서 휴리스틱 +
동일 target_path 체이닝으로 `depends_on` 을 계산하고, 위상정렬로 `wave`(마일스톤)
를 배정한다. `plan.json`(오케스트레이터 실행용, CE-290 입력) 과 사람이 읽는
`modernization-plan.md` 렌더링도 이 모듈이 담당한다.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

# 카테고리별 기본 실행 순서 — 스키마/런타임 변경(migrate/upgrade/replace)이 먼저,
# 구조 정리(refactor)가 다음, 삭제(remove)가 마지막.
_CATEGORY_ORDER: dict[str, int] = {
    "migrate": 0,
    "upgrade": 1,
    "replace": 1,
    "refactor": 2,
    "remove": 3,
}

# target_path 접두어 → 담당 에이전트 (CLAUDE.md 모듈 지도와 동일 축)
_AGENT_PATH_PREFIXES: list[tuple[str, str]] = [
    ("clickeye-contracts/", "contracts"),
    ("clickeye-infra/", "infra"),
    ("clickeye-web/", "web"),
    ("clickeye-api/", "api"),
    ("clickeye-agent/", "agent"),
]


class PlanValidationError(ValueError):
    """DAG 구성이 위상정렬 불가능(사이클 존재)할 때 발생."""


def infer_agent(target_path: str | None, category: str) -> str:
    """target_path 접두어로 담당 에이전트 추론. 매칭 없으면 'fullstack'."""
    if target_path:
        for prefix, agent in _AGENT_PATH_PREFIXES:
            if target_path.startswith(prefix):
                return agent
    return "fullstack"


def build_dependencies(recs: list[dict[str, Any]]) -> list[list[int]]:
    """idx 기반 depends_on 배열 계산.

    1) 동일 target_path 를 공유하는 권장안은 idx 오름차순으로 순차 의존.
    2) 카테고리 순서 그룹 간에는 이전 그룹의 대표 1건(최소 idx)에만 의존시켜
       N*M 엣지 폭발을 방지하면서도 웨이브 순서를 강제한다.
    """
    by_path: dict[str, list[int]] = defaultdict(list)
    for idx, rec in enumerate(recs):
        path = rec.get("target_path")
        if path:
            by_path[path].append(idx)

    deps: list[list[int]] = [[] for _ in recs]

    for idx_list in by_path.values():
        ordered = sorted(idx_list)
        for prev, cur in zip(ordered, ordered[1:], strict=False):
            deps[cur].append(prev)

    order_buckets: dict[int, list[int]] = defaultdict(list)
    for idx, rec in enumerate(recs):
        order = _CATEGORY_ORDER.get(str(rec.get("category", "")), 1)
        order_buckets[order].append(idx)

    sorted_orders = sorted(order_buckets)
    for i in range(1, len(sorted_orders)):
        prev_order = sorted_orders[i - 1]
        cur_order = sorted_orders[i]
        anchor = min(order_buckets[prev_order])
        for idx in order_buckets[cur_order]:
            if anchor not in deps[idx]:
                deps[idx].append(anchor)

    return deps


def compute_waves(depends_on: list[list[int]]) -> list[int]:
    """위상정렬(Kahn) 기반 wave 배정. 사이클 검출 시 PlanValidationError."""
    n = len(depends_on)
    indegree = [0] * n
    children: list[list[int]] = [[] for _ in range(n)]

    for idx, deps in enumerate(depends_on):
        for d in deps:
            if not isinstance(d, int) or d < 0 or d >= n or d == idx:
                raise PlanValidationError(f"권장안 {idx} 의 의존성 인덱스가 유효하지 않습니다: {d}")
            children[d].append(idx)
            indegree[idx] += 1

    wave = [0] * n
    queue: deque[int] = deque(i for i in range(n) if indegree[i] == 0)
    visited = 0

    while queue:
        cur = queue.popleft()
        visited += 1
        for nxt in children[cur]:
            wave[nxt] = max(wave[nxt], wave[cur] + 1)
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if visited != n:
        raise PlanValidationError("의존성 그래프에 사이클이 존재해 위상정렬이 불가능합니다.")

    return wave


def build_plan(recs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """각 rec 에 대해 idx/depends_on/wave/assigned_agent 를 idx 순서로 반환."""
    depends_on = build_dependencies(recs)
    waves = compute_waves(depends_on)
    return [
        {
            "idx": idx,
            "depends_on": depends_on[idx],
            "wave": waves[idx],
            "assigned_agent": infer_agent(rec.get("target_path"), str(rec.get("category", ""))),
        }
        for idx, rec in enumerate(recs)
    ]


def build_plan_json(
    *,
    session_id: str,
    recs: list[dict[str, Any]],
) -> dict[str, Any]:
    """오케스트레이터(CE-290) 입력용 기계 포맷.

    recs 는 이미 idx/depends_on/wave/assigned_agent/title/effort/risk/category 를
    갖고 있어야 한다 (DB 에 영속된 ModernizeRecommendation 을 dict 화한 것).
    """
    waves_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for rec in recs:
        wave = int(rec.get("wave", 0))
        waves_map[wave].append(
            {
                "rec_id": rec.get("id"),
                "idx": rec.get("idx"),
                "title": rec.get("title"),
                "category": rec.get("category"),
                "effort": rec.get("effort"),
                "risk": rec.get("risk"),
                "assigned_agent": rec.get("assigned_agent"),
                "depends_on": rec.get("depends_on") or [],
            }
        )

    return {
        "session_id": session_id,
        "waves": [
            {"wave": wave, "tasks": tasks} for wave, tasks in sorted(waves_map.items())
        ],
    }


def render_plan_markdown(recs: list[dict[str, Any]]) -> str:
    """웨이브별 태스크 목록 markdown 렌더링 (`modernization-plan.md`)."""
    waves_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for rec in recs:
        waves_map[int(rec.get("wave", 0))].append(rec)

    lines = ["# 현대화 실행 계획", ""]
    if not recs:
        lines.append("(권장안이 없어 계획을 생성할 수 없습니다.)")
        return "\n".join(lines)

    for wave in sorted(waves_map):
        lines.append(f"## Wave {wave}")
        lines.append("")
        for rec in sorted(waves_map[wave], key=lambda r: r.get("idx", 0)):
            deps = rec.get("depends_on") or []
            dep_str = f" (선행: {', '.join(f'#{d}' for d in deps)})" if deps else ""
            lines.append(
                f"- **#{rec.get('idx')} {rec.get('title')}** "
                f"— 담당: `{rec.get('assigned_agent')}` · "
                f"effort: {rec.get('effort')} · risk: {rec.get('risk')}{dep_str}"
            )
        lines.append("")

    return "\n".join(lines)
