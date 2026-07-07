"""finalize._register_depends_on_relations 단위 테스트 (Phase 4 — depends_on → Linear blocks)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.models.modernize_recommendation import ModernizeRecommendation
from app.services.modernize.finalize import _register_depends_on_relations

pytestmark = pytest.mark.no_db


def _rec(idx: int, linear_issue_id: str | None, depends_on: list[int]) -> ModernizeRecommendation:
    return ModernizeRecommendation(
        idx=idx,
        category="upgrade",
        title=f"rec-{idx}",
        linear_issue_id=linear_issue_id,
        depends_on=depends_on,
    )


def test_registers_relation_for_each_dependency_edge() -> None:
    recs = [_rec(0, "issue-0", []), _rec(1, "issue-1", [0])]
    calls: list[tuple[str, str]] = []

    def fake_create_issue_relation(
        _api_key: str, *, blocking_issue_id: str, blocked_issue_id: str
    ) -> bool:
        calls.append((blocking_issue_id, blocked_issue_id))
        return True

    with patch(
        "app.services.modernize.finalize.linear_service.create_issue_relation",
        side_effect=fake_create_issue_relation,
    ):
        _register_depends_on_relations("fake-key", recs)

    assert calls == [("issue-0", "issue-1")]


def test_skips_edges_to_deselected_or_unregistered_recs() -> None:
    recs = [
        _rec(0, None, []),  # 선택 해제 또는 등록 실패 — linear_issue_id 없음
        _rec(1, "issue-1", [0]),  # 의존 대상(idx=0) 이 Linear 에 없음 → skip
    ]
    with patch(
        "app.services.modernize.finalize.linear_service.create_issue_relation"
    ) as mock_create:
        _register_depends_on_relations("fake-key", recs)

    mock_create.assert_not_called()


def test_relation_failure_does_not_raise() -> None:
    recs = [_rec(0, "issue-0", []), _rec(1, "issue-1", [0])]

    with patch(
        "app.services.modernize.finalize.linear_service.create_issue_relation",
        side_effect=RuntimeError("boom"),
    ):
        _register_depends_on_relations("fake-key", recs)  # 예외 없이 종료되어야 함
