"""linear_watcher의 서브태스크 재귀 확장 로직 단위 테스트.

Agent_PR_Monitor에서 이식된 fetch_children / expand_to_leaves / fetch_queued_issues
함수의 동작을 검증한다.

Usage:
    cd ClickEye && pytest scripts/tests/test_linear_watcher.py -v
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

# scripts/ 디렉토리를 import path에 추가 (linear_watcher import 위해)
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import linear_watcher  # noqa: E402


# ── 픽스처 헬퍼 ───────────────────────────────────────────────────────────────


def _issue(
    id: str,
    identifier: str,
    title: str = "Test",
    state: str = "DayQueued",
    priority: int = 3,
) -> dict:
    """Linear 이슈 dict 픽스처 생성."""
    return {
        "id": id,
        "identifier": identifier,
        "title": title,
        "description": "",
        "priority": priority,
        "dueDate": None,
        "url": f"https://linear.app/test/{identifier}",
        "labels": {"nodes": []},
        "state": {"id": "s1", "name": state},
    }


# ── fetch_children ────────────────────────────────────────────────────────────


def test_fetch_children_returns_nodes():
    """fetch_children은 GraphQL 응답의 issues.nodes를 그대로 반환한다."""
    children = [_issue("c1", "CE-2"), _issue("c2", "CE-3")]
    with patch.object(
        linear_watcher,
        "linear_request",
        return_value={"issues": {"nodes": children}},
    ) as mock_req:
        result = linear_watcher.fetch_children("key", "team", "parent-id")
    assert result == children
    mock_req.assert_called_once()
    args, kwargs = mock_req.call_args
    # 변수에 parentId 전달 확인
    assert args[2]["parentId"] == "parent-id"


def test_fetch_children_empty_response():
    """linear_request가 None 반환 시 빈 리스트."""
    with patch.object(linear_watcher, "linear_request", return_value=None):
        assert linear_watcher.fetch_children("k", "t", "p") == []


# ── expand_to_leaves ──────────────────────────────────────────────────────────


def test_expand_leaf_returns_self():
    """자식이 없으면 자기 자신을 리스트로 반환."""
    parent = _issue("p1", "CE-1")
    with patch.object(linear_watcher, "fetch_children", return_value=[]):
        assert linear_watcher.expand_to_leaves("k", "t", parent) == [parent]


def test_expand_skips_terminal_children():
    """Done/Canceled/Duplicate 상태 자식은 건너뛴다."""
    parent = _issue("p1", "CE-1")
    child_done = _issue("c1", "CE-2", state="Done")
    child_cancel = _issue("c2", "CE-3", state="Canceled")
    child_dup = _issue("c3", "CE-4", state="Duplicate")
    child_active = _issue("c4", "CE-5", state="DayQueued")

    def fake_children(_k, _t, parent_id):
        if parent_id == "p1":
            return [child_done, child_cancel, child_dup, child_active]
        return []

    with patch.object(linear_watcher, "fetch_children", side_effect=fake_children):
        result = linear_watcher.expand_to_leaves("k", "t", parent)
    assert result == [child_active]


def test_expand_recursive_grandchildren():
    """다단계 계층(grandchild)도 재귀로 펼친다."""
    parent = _issue("p1", "CE-1")
    child = _issue("c1", "CE-2")
    grandchild_1 = _issue("g1", "CE-3")
    grandchild_2 = _issue("g2", "CE-4")

    def fake_children(_k, _t, parent_id):
        return {
            "p1": [child],
            "c1": [grandchild_1, grandchild_2],
            "g1": [],
            "g2": [],
        }.get(parent_id, [])

    with patch.object(linear_watcher, "fetch_children", side_effect=fake_children):
        result = linear_watcher.expand_to_leaves("k", "t", parent)
    assert result == [grandchild_1, grandchild_2]


def test_expand_terminal_state_blocks_recursion():
    """Done 자식은 그 아래 손자가 있어도 재귀에 들어가지 않는다."""
    parent = _issue("p1", "CE-1")
    child_done = _issue("c1", "CE-2", state="Done")
    grandchild = _issue("g1", "CE-3")

    def fake_children(_k, _t, parent_id):
        # c1 자식 조회를 호출하면 안 됨 (Done이라 skip)
        return {
            "p1": [child_done],
            "c1": [grandchild],  # 도달 안 됨
        }.get(parent_id, [])

    with patch.object(linear_watcher, "fetch_children", side_effect=fake_children):
        result = linear_watcher.expand_to_leaves("k", "t", parent)
    assert result == []  # 활성 리프 없음


# ── fetch_queued_issues 통합 ──────────────────────────────────────────────────


def test_fetch_queued_expands_parents_to_leaves():
    """부모만 큐 상태일 때 자식 리프들로 펼쳐서 반환한다.

    parent_identifier 메타도 정확히 주입되는지 확인.
    """
    parent = _issue("p1", "CE-1", state="DayQueued")
    child1 = _issue("c1", "CE-2", state="Backlog")
    child2 = _issue("c2", "CE-3", state="Backlog")

    # 초기 폴링: 부모 1개만 반환
    def fake_linear_request(_k, _q, vars):
        if "parentId" in vars:
            return {"issues": {"nodes": []}}  # 자식의 자식 없음
        return {"issues": {"nodes": [parent]}}

    def fake_fetch_children(_k, _t, parent_id):
        return {"p1": [child1, child2]}.get(parent_id, [])

    with patch.object(linear_watcher, "linear_request", side_effect=fake_linear_request), \
         patch.object(linear_watcher, "fetch_children", side_effect=fake_fetch_children):
        result = linear_watcher.fetch_queued_issues("k", "t")

    # 두 자식만 리프로 펼쳐짐, 부모는 결과에서 제외
    assert len(result) == 2
    ids = [r["id"] for r in result]
    assert "c1" in ids
    assert "c2" in ids
    assert "p1" not in ids
    # 자식에 _parent_identifier 메타가 주입됨
    for r in result:
        assert r["_parent_identifier"] == "CE-1"


def test_fetch_queued_keeps_leaf_issues_unchanged():
    """자식 없는 일반 큐 이슈는 그대로 (백워드 호환)."""
    leaf = _issue("l1", "CE-1", state="DayQueued")

    def fake_linear_request(_k, _q, vars):
        if "parentId" in vars:
            return {"issues": {"nodes": []}}
        return {"issues": {"nodes": [leaf]}}

    with patch.object(linear_watcher, "linear_request", side_effect=fake_linear_request):
        result = linear_watcher.fetch_queued_issues("k", "t")

    assert len(result) == 1
    assert result[0]["id"] == "l1"
    # 리프 자체는 parent_identifier 미주입
    assert "_parent_identifier" not in result[0]


def test_fetch_queued_dedupes_overlapping_children():
    """동일 자식이 여러 부모를 통해 노출되어도 중복 제거된다."""
    parent_a = _issue("pa", "CE-1", state="DayQueued")
    parent_b = _issue("pb", "CE-2", state="DayQueued")
    shared_child = _issue("c1", "CE-3", state="Backlog")

    def fake_linear_request(_k, _q, vars):
        if "parentId" in vars:
            return {"issues": {"nodes": []}}
        return {"issues": {"nodes": [parent_a, parent_b]}}

    def fake_fetch_children(_k, _t, parent_id):
        # 두 부모가 같은 자식을 가짐
        return {"pa": [shared_child], "pb": [shared_child]}.get(parent_id, [])

    with patch.object(linear_watcher, "linear_request", side_effect=fake_linear_request), \
         patch.object(linear_watcher, "fetch_children", side_effect=fake_fetch_children):
        result = linear_watcher.fetch_queued_issues("k", "t")

    # 동일 child가 중복 없이 1번만 등장
    assert len(result) == 1
    assert result[0]["id"] == "c1"


# ── extract_task_info / save_task_mapping 통합 ────────────────────────────────


def test_extract_task_info_propagates_parent_identifier():
    """expand_to_leaves가 주입한 _parent_identifier가 task dict로 전파된다."""
    leaf = _issue("c1", "CE-2", state="Backlog")
    leaf["_parent_identifier"] = "CE-1"

    task = linear_watcher.extract_task_info(leaf)

    assert task["parent_identifier"] == "CE-1"
    assert task["identifier"] == "CE-2"


def test_extract_task_info_no_parent_for_top_level():
    """리프 자체(자식 없는 일반 이슈)는 parent_identifier가 None."""
    leaf = _issue("l1", "CE-1", state="DayQueued")
    task = linear_watcher.extract_task_info(leaf)
    assert task["parent_identifier"] is None


# ── incomplete_blockers (blockedBy 가드) ─────────────────────────────────────


def _with_blocker(identifier: str, blocker_id: str, blocker_state_type: str, rel_type: str = "blocks") -> dict:
    """inverseRelations 로 blocker 를 가진 이슈 픽스처."""
    issue = _issue("x", identifier)
    issue["inverseRelations"] = {
        "nodes": [
            {"type": rel_type, "issue": {"identifier": blocker_id, "state": {"type": blocker_state_type}}}
        ]
    }
    return issue


def test_incomplete_blockers_none_when_blocker_completed():
    """선행 이슈가 완료(completed)면 차단 없음."""
    issue = _with_blocker("CE-285", "CE-284", "completed")
    assert linear_watcher.incomplete_blockers(issue) == []


def test_incomplete_blockers_flags_started_blocker():
    """선행 이슈가 미완료(started 등)면 그 identifier 를 반환."""
    issue = _with_blocker("CE-285", "CE-284", "started")
    assert linear_watcher.incomplete_blockers(issue) == ["CE-284"]


def test_incomplete_blockers_canceled_treated_as_done():
    """취소(canceled)된 선행은 차단으로 보지 않는다."""
    issue = _with_blocker("CE-285", "CE-284", "canceled")
    assert linear_watcher.incomplete_blockers(issue) == []


def test_incomplete_blockers_ignores_non_blocks_relation():
    """related/duplicate 관계는 무시한다 (blocks 만 게이팅)."""
    issue = _with_blocker("CE-285", "CE-9", "started", rel_type="related")
    assert linear_watcher.incomplete_blockers(issue) == []


def test_incomplete_blockers_empty_when_no_relations():
    """관계 정보가 없으면 빈 리스트."""
    assert linear_watcher.incomplete_blockers(_issue("x", "CE-1")) == []
