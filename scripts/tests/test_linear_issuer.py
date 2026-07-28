"""티켓 전량 발급기 테스트 (다프로젝트화 P6, D-12).

검증 축:
  1. 검증 fail-closed — 스키마·중복 키·미지 참조·자기 참조·순환·폭주 상한 전부
     **네트워크 호출 전** 거부(발급 0건).
  2. 위상 정렬 — 결정적 순서, 순환 시 관련 티켓 명시.
  3. 역위상 승격 — "부분 실패 = 실행 0건" 불변식의 근거: 어느 접두 구간까지 승격돼도
     승격분은 전부 미승격 선행에 막힌다.
  4. 3상 발급 흐름(linear_request 목킹) — Backlog 생성 → blocks 배선 → 승격 순서,
     중간 실패 시 RuntimeError 에 생성 이슈 힌트 포함 + 이후 상 미진행.

Usage:
    cd ClickEye && pytest scripts/tests/test_linear_issuer.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import linear_issuer as li  # noqa: E402

T = [
    {"key": "T1", "title": "설계: 스키마"},
    {"key": "T2", "title": "구현: API", "depends_on": ["T1"]},
    {"key": "T3", "title": "구현: UI", "depends_on": ["T1"]},
    {"key": "T4", "title": "통합 테스트", "depends_on": ["T2", "T3"]},
]


# ── 1. 검증 fail-closed ─────────────────────────────────────────────────────


def test_valid_decomposition_passes():
    tickets = li.validate_decomposition({"tickets": T})
    assert [t["key"] for t in tickets] == ["T1", "T2", "T3", "T4"]


@pytest.mark.parametrize(
    "bad,fragment",
    [
        ([], "최상위"),
        ({"tickets": []}, "비어있지 않은 배열"),
        ({"tickets": T, "extra": 1}, "알 수 없는 키"),
        ({"tickets": [{"key": "T1"}]}, "title"),
        ({"tickets": [{"title": "무제"}]}, "key"),
        ({"tickets": [{"key": "T1", "title": "a", "oops": 1}]}, "알 수 없는 키"),
        ({"tickets": [{"key": "T1", "title": "a"}, {"key": "T1", "title": "b"}]}, "중복"),
        ({"tickets": [{"key": "T1", "title": "a", "priority": 9}]}, "0~4"),
        ({"tickets": [{"key": "T1", "title": "a", "priority": True}]}, "0~4"),
        ({"tickets": [{"key": "T1", "title": "a", "labels": [""]}]}, "labels"),
        ({"tickets": [{"key": "T1", "title": "a", "depends_on": ["없는키"]}]}, "미지의 선행"),
        ({"tickets": [{"key": "T1", "title": "a", "depends_on": ["T1"]}]}, "자기 자신"),
    ],
)
def test_fail_closed_before_any_network(bad, fragment, monkeypatch):
    """불량 분해는 발급 0건 — linear_request 가 절대 호출되지 않아야 한다."""
    def _no_network(*a, **k):  # pragma: no cover - 호출 자체가 실패
        raise AssertionError("검증 실패 입력인데 네트워크 호출 발생")

    monkeypatch.setattr(li, "linear_request", _no_network)
    with pytest.raises(li.DecompositionError, match=fragment):
        li.validate_decomposition(bad)


def test_ticket_flood_capped():
    flood = {"tickets": [{"key": f"T{i}", "title": "x"} for i in range(li.MAX_TICKETS + 1)]}
    with pytest.raises(li.DecompositionError, match="상한"):
        li.validate_decomposition(flood)


# ── 2. 위상 정렬 ────────────────────────────────────────────────────────────


def test_topo_sort_roots_first_and_deterministic():
    order = li.topo_sort(T)
    assert order[0] == "T1" and order[-1] == "T4"
    assert order.index("T2") < order.index("T4")
    assert order.index("T3") < order.index("T4")
    assert li.topo_sort(T) == order  # 결정적


def test_topo_sort_cycle_names_participants():
    cyc = [
        {"key": "A", "title": "a", "depends_on": ["B"]},
        {"key": "B", "title": "b", "depends_on": ["A"]},
        {"key": "C", "title": "c"},
    ]
    with pytest.raises(li.DecompositionError, match="순환") as ei:
        li.topo_sort(cyc)
    assert "A" in str(ei.value) and "B" in str(ei.value)
    assert "C" not in str(ei.value)  # 무고한 티켓은 순환 목록에 없다


# ── 3. 역위상 승격 불변식 ────────────────────────────────────────────────────


def test_promotion_order_is_reverse_topo():
    promo = li.promotion_order(T)
    assert promo[0] == "T4" and promo[-1] == "T1"


def test_partial_promotion_never_executable():
    """불변식 증명: 승격이 어느 접두 구간에서 멈춰도 실행 가능한 티켓은 0이다.

    실행 가능 = watcher 기준 "선행이 없거나, 모든 선행이 completed". 발급 시점에
    completed 는 존재하지 않으므로 실행 가능 = **뿌리(무의존) 티켓뿐**이다.
    역위상 승격은 뿌리를 맨 끝에 두므로, 부분 실패(cut < 전체)에서는 뿌리가
    승격돼 있을 수 없다 — 의존 티켓은 승격됐어도 선행 미완료로 watcher 가 차단한다.
    """
    deps = {t["key"]: set(t.get("depends_on") or []) for t in T}
    promo = li.promotion_order(T)
    for cut in range(len(promo)):  # cut 개까지만 승격된 모든 부분 실패 시나리오
        promoted_roots = [k for k in promo[:cut] if not deps[k]]
        assert promoted_roots == [], (
            f"부분 실패(cut={cut})인데 뿌리 {promoted_roots} 가 승격됨 — 즉시 실행 가능"
        )


# ── 4. 3상 발급 흐름 (linear_request 목킹) ──────────────────────────────────


class _FakeLinear:
    """linear_request 대역 — 호출을 기록하고 상별 실패를 주입할 수 있다."""

    def __init__(self, fail_at: str | None = None, fail_key: str | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.fail_at = fail_at  # "create" | "relation" | "update"
        self.fail_key = fail_key
        self._seq = 0

    def __call__(self, api_key, query, variables=None):
        kind = (
            "create" if "issueCreate" in query
            else "relation" if "issueRelationCreate" in query
            else "update" if "issueUpdate" in query
            else "other"
        )
        self.calls.append((kind, variables or {}))
        if kind == "create":
            title = variables["input"]["title"]
            if self.fail_at == "create" and self.fail_key in title:
                return {"issueCreate": None}
            self._seq += 1
            return {
                "issueCreate": {
                    "issue": {
                        "id": f"iid-{self._seq}",
                        "identifier": f"CE-{900 + self._seq}",
                        "title": title,
                    }
                }
            }
        if kind == "relation":
            if self.fail_at == "relation":
                return {}
            return {"issueRelationCreate": {"issueRelation": {"id": "rel"}}}
        if kind == "update":
            if self.fail_at == "update" and variables["issueId"] == self.fail_key:
                return {"issueUpdate": {"success": False}}
            return {"issueUpdate": {"success": True}}
        return {}


@pytest.fixture(autouse=True)
def _env_and_states(monkeypatch):
    monkeypatch.setattr(li, "get_env", lambda team=None: ("key", "team"))
    monkeypatch.setattr(
        li, "find_state_id",
        lambda api_key, team_id, name: {"Backlog": "st-backlog",
                                        "NightQueued": "st-night",
                                        "DayQueued": "st-day"}.get(name),
    )
    monkeypatch.setattr(li, "_resolve_label_ids", lambda *a: [])
    yield


def test_issue_all_three_phases_in_order(monkeypatch):
    fake = _FakeLinear()
    monkeypatch.setattr(li, "linear_request", fake)

    ledger = li.issue_all(li.validate_decomposition({"tickets": T}),
                          target_state="NightQueued", title_prefix="[수주] ")

    # 원장: 입력 순서 + 로컬 키 ↔ Linear 식별자 대응
    assert [e["key"] for e in ledger] == ["T1", "T2", "T3", "T4"]
    assert all(e["identifier"].startswith("CE-") for e in ledger)

    kinds = [k for k, _ in fake.calls]
    # 상 순서: create 전량 → relation 전량 → update 전량 (섞이지 않는다)
    assert kinds == ["create"] * 4 + ["relation"] * 4 + ["update"] * 4
    # 1상은 전부 Backlog 로 생성됐다(비활성 — 부분 실패 시 실행 불가의 근거)
    creates = [v for k, v in fake.calls if k == "create"]
    assert all(v["input"]["stateId"] == "st-backlog" for v in creates)
    assert creates[0]["input"]["title"].startswith("[수주] ")
    # 3상 승격은 역위상 — 첫 승격은 잎(T4의 iid), 마지막은 뿌리(T1의 iid)
    updates = [v for k, v in fake.calls if k == "update"]
    id_by_key = {e["key"]: e["issue_id"] for e in ledger}
    assert updates[0]["issueId"] == id_by_key["T4"]
    assert updates[-1]["issueId"] == id_by_key["T1"]
    assert all(v["stateId"] == "st-night" for v in updates)


def test_create_failure_stops_and_reports_created(monkeypatch):
    fake = _FakeLinear(fail_at="create", fail_key="구현: UI")  # T3 에서 실패
    monkeypatch.setattr(li, "linear_request", fake)

    with pytest.raises(RuntimeError, match="1상 생성 실패") as ei:
        li.issue_all(li.validate_decomposition({"tickets": T}), target_state="NightQueued")
    # 그때까지 생성된 이슈(수동 정리 힌트)가 메시지에 있다
    assert "T1=CE-901" in str(ei.value)
    # 배선/승격 상은 진행되지 않았다 — Backlog 잔류 = 실행 불가
    assert not [k for k, _ in fake.calls if k in ("relation", "update")]


def test_relation_failure_leaves_all_inert(monkeypatch):
    fake = _FakeLinear(fail_at="relation")
    monkeypatch.setattr(li, "linear_request", fake)

    with pytest.raises(RuntimeError, match="2상 배선 실패"):
        li.issue_all(li.validate_decomposition({"tickets": T}), target_state="NightQueued")
    assert not [k for k, _ in fake.calls if k == "update"]  # 승격 0건 — 전량 비활성


def test_update_failure_message_mentions_invariant(monkeypatch):
    # 첫 승격 대상(잎 T4 = iid-4)에서 실패 주입
    fake = _FakeLinear(fail_at="update", fail_key="iid-4")
    monkeypatch.setattr(li, "linear_request", fake)

    with pytest.raises(RuntimeError, match="3상 승격 실패"):
        li.issue_all(li.validate_decomposition({"tickets": T}), target_state="NightQueued")
    # 승격 시도는 1건뿐 — 이후 즉시 중단
    assert len([k for k, _ in fake.calls if k == "update"]) == 1


def test_missing_state_fails_before_create(monkeypatch):
    fake = _FakeLinear()
    monkeypatch.setattr(li, "linear_request", fake)
    monkeypatch.setattr(li, "find_state_id", lambda *a: None)

    with pytest.raises(RuntimeError, match="상태 조회 실패"):
        li.issue_all(li.validate_decomposition({"tickets": T}), target_state="NightQueued")
    assert fake.calls == []  # 생성 0건
