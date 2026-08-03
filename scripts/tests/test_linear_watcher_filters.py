"""linear_watcher 의 제목 접두사 필터 + --check-only 단위 테스트 (P5/CE-346).

디스패처가 쓰는 두 기능을 덮는다:
  · --exclude-prefix — 전용 러너가 맡은 프로젝트를 단일 러너에서 빼는 코디네이션 필터
  · --check-only     — Queued 존재 여부만 확인하고 **어떤 파일도 쓰지 않는다**
                       (fix_plan / .task_mapping.json / .ralph/tasks 오염 금지)

Usage:
    cd ClickEye && pytest scripts/tests/test_linear_watcher_filters.py -v
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

# scripts/ 디렉토리를 import path에 추가 (linear_watcher import 위해)
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import linear_watcher  # noqa: E402


def _issue(identifier: str, title: str) -> dict:
    """제목 필터 검증에 필요한 최소 이슈 픽스처."""
    return {
        "id": f"id-{identifier}",
        "identifier": identifier,
        "title": title,
        "description": "",
        "priority": 3,
        "url": "",
        "labels": {"nodes": []},
        "state": {"id": "s1", "name": "Queued"},
    }


NODES = [
    _issue("CE-1", "[수주:aaa11111] 로그인 구현"),
    _issue("CE-2", "[수주:bbb22222] 결제 연동"),
    _issue("CE-3", "내부 리팩터링"),
    _issue("CE-4", "[수주:aaa11111] 회원가입"),
]


def _titles(nodes: list[dict]) -> list[str]:
    return [n["identifier"] for n in nodes]


# ── apply_title_filters (순수 함수) ───────────────────────────────────────────


def test_no_filters_is_identity():
    """둘 다 미지정이면 입력 그대로 — 기존 호출부 무회귀."""
    assert linear_watcher.apply_title_filters(NODES) == NODES


def test_include_only():
    got = linear_watcher.apply_title_filters(NODES, title_prefix="[수주:aaa11111] ")
    assert _titles(got) == ["CE-1", "CE-4"]


def test_exclude_only():
    got = linear_watcher.apply_title_filters(
        NODES, exclude_prefixes=["[수주:aaa11111] "]
    )
    assert _titles(got) == ["CE-2", "CE-3"]


def test_exclude_multiple_prefixes():
    """--exclude-prefix 는 반복 지정 가능 — 전용 러너가 여럿일 때 전부 뺀다."""
    got = linear_watcher.apply_title_filters(
        NODES, exclude_prefixes=["[수주:aaa11111] ", "[수주:bbb22222] "]
    )
    assert _titles(got) == ["CE-3"]


def test_include_then_exclude_order():
    """적용 순서는 include → exclude. 같은 접두사를 둘 다 주면 결과는 빈 목록."""
    got = linear_watcher.apply_title_filters(
        NODES,
        title_prefix="[수주:aaa11111] ",
        exclude_prefixes=["[수주:aaa11111] "],
    )
    assert got == []


def test_include_and_disjoint_exclude():
    got = linear_watcher.apply_title_filters(
        NODES,
        title_prefix="[수주:",
        exclude_prefixes=["[수주:bbb22222] "],
    )
    assert _titles(got) == ["CE-1", "CE-4"]


def test_empty_prefix_entries_ignored():
    """빈 문자열이 섞여도 전체 제외로 번지지 않는다(모든 제목이 ''로 시작하므로 위험)."""
    got = linear_watcher.apply_title_filters(NODES, exclude_prefixes=["", None])
    assert got == NODES


def test_missing_title_treated_as_empty():
    nodes = [{"id": "x", "identifier": "CE-9"}]
    assert linear_watcher.apply_title_filters(nodes, title_prefix="[수주:") == []
    assert linear_watcher.apply_title_filters(nodes, exclude_prefixes=["[수주:"]) == nodes


# ── fetch_queued_issues 경유 (필터가 실제로 배선돼 있는지) ────────────────────


def test_fetch_queued_issues_applies_exclude():
    """조회 결과에 exclude 가 적용되고, 확장(fetch_children) 전에 걸러진다."""
    payload = {"issues": {"nodes": NODES}}
    with patch.object(linear_watcher, "linear_request", return_value=payload), \
         patch.object(linear_watcher, "fetch_children", return_value=[]):
        got = linear_watcher.fetch_queued_issues(
            "key", "team", exclude_prefixes=["[수주:aaa11111] "]
        )
    assert _titles(got) == ["CE-2", "CE-3"]


# ── --check-only (파일 무기록) ────────────────────────────────────────────────


@pytest.fixture()
def scratch_paths(tmp_path, monkeypatch):
    """watcher 의 쓰기 경로 3종을 임시 경로로 돌린다 — 실제 .ralph 오염 없이 검증."""
    fix_plan = tmp_path / "fix_plan.md"
    mapping = tmp_path / ".task_mapping.json"
    tasks_dir = tmp_path / "tasks"
    monkeypatch.setattr(linear_watcher, "FIX_PLAN_PATH", str(fix_plan))
    monkeypatch.setattr(linear_watcher, "TASK_MAPPING_PATH", str(mapping))
    monkeypatch.setattr(linear_watcher, "TASKS_DIR", str(tasks_dir))
    monkeypatch.setenv("FLOWOPS_LINEAR_WATCHER", "true")
    monkeypatch.delenv("WATCHER_EXCLUDE_PREFIXES", raising=False)
    return fix_plan, mapping, tasks_dir


def _run_main(argv: list[str]) -> int:
    """main() 을 argv 로 실행하고 종료코드를 돌려준다."""
    with patch.object(sys, "argv", ["linear_watcher.py", *argv]), \
         patch.object(linear_watcher, "get_env", return_value=("key", "team")):
        with pytest.raises(SystemExit) as exc:
            linear_watcher.main()
    return exc.value.code


def test_check_only_found_exits_0_and_writes_nothing(scratch_paths, capsys):
    fix_plan, mapping, tasks_dir = scratch_paths
    with patch.object(linear_watcher, "fetch_queued_issues", return_value=NODES[:2]), \
         patch.object(linear_watcher, "update_issue_state") as upd:
        code = _run_main(["--check-only", "--title-prefix", "[수주:aaa11111] "])

    assert code == 0
    assert not fix_plan.exists()
    assert not mapping.exists()
    assert not tasks_dir.exists()
    upd.assert_not_called()          # Linear 상태 전이도 없다(관측 전용)
    assert "FOUND" in capsys.readouterr().out


def test_check_only_empty_exits_2(scratch_paths):
    fix_plan, mapping, tasks_dir = scratch_paths
    with patch.object(linear_watcher, "fetch_queued_issues", return_value=[]):
        code = _run_main(["--check-only"])

    assert code == 2
    assert not fix_plan.exists()
    assert not mapping.exists()
    assert not tasks_dir.exists()


def test_check_only_passes_filters_through(scratch_paths):
    """CLI 인자가 fetch_queued_issues 로 그대로 전달되는지(디스패처 호출 형태)."""
    with patch.object(
        linear_watcher, "fetch_queued_issues", return_value=NODES[:1]
    ) as fetch:
        _run_main([
            "--check-only",
            "--title-prefix", "[수주:aaa11111] ",
            "--exclude-prefix", "[수주:bbb22222] ",
            "--exclude-prefix", "[수주:ccc33333] ",
        ])

    _, kwargs = fetch.call_args
    assert kwargs["title_prefix"] == "[수주:aaa11111] "
    assert kwargs["exclude_prefixes"] == ["[수주:bbb22222] ", "[수주:ccc33333] "]


def test_default_invocation_keeps_no_filters(scratch_paths):
    """--dry-run 기본 호출은 필터 없이(None) 전달 — 기존 동작 무회귀."""
    with patch.object(
        linear_watcher, "fetch_queued_issues", return_value=NODES[:1]
    ) as fetch:
        _run_main(["--dry-run"])

    _, kwargs = fetch.call_args
    assert kwargs["title_prefix"] is None
    assert kwargs["exclude_prefixes"] is None


def test_check_only_disabled_exits_2(scratch_paths, monkeypatch):
    """토글 비활성 시 --check-only 는 exit 2.

    check_enabled 의 기본 동작(exit 0)을 그대로 쓰면 디스패처가 "Queued 있음"으로 읽고
    러너를 스폰한다 — 비활성은 "할 일 없음"이어야 한다.
    """
    monkeypatch.setenv("FLOWOPS_LINEAR_WATCHER", "false")
    with patch.object(linear_watcher, "fetch_queued_issues") as fetch:
        code = _run_main(["--check-only"])

    assert code == 2
    fetch.assert_not_called()          # Linear 조회에 도달하지도 않는다


def test_disabled_other_modes_still_exit_0(scratch_paths, monkeypatch):
    """비활성 시 --check-only 가 아닌 모드는 기존대로 exit 0(회귀 0)."""
    monkeypatch.setenv("FLOWOPS_LINEAR_WATCHER", "false")
    with patch.object(linear_watcher, "fetch_queued_issues") as fetch:
        code = _run_main(["--dry-run"])

    assert code == 0
    fetch.assert_not_called()


# ── WATCHER_EXCLUDE_PREFIXES (env 경유 exclude — 파이프라인 본체 무수정 경로) ──


def test_env_exclude_alone(monkeypatch):
    monkeypatch.setenv("WATCHER_EXCLUDE_PREFIXES", "[수주:aaa11111] ")
    assert linear_watcher.resolve_exclude_prefixes(None) == ["[수주:aaa11111] "]


def test_env_exclude_tab_separated_multiple(monkeypatch):
    """구분자는 탭 — 접두사가 공백을 포함하므로 공백 구분은 안전하지 않다."""
    monkeypatch.setenv(
        "WATCHER_EXCLUDE_PREFIXES", "[수주:aaa11111] \t[수주:bbb22222] "
    )
    assert linear_watcher.resolve_exclude_prefixes(None) == [
        "[수주:aaa11111] ",
        "[수주:bbb22222] ",
    ]


def test_env_and_cli_merge_dedup(monkeypatch):
    monkeypatch.setenv("WATCHER_EXCLUDE_PREFIXES", "[수주:bbb22222] \t[수주:aaa11111] ")
    got = linear_watcher.resolve_exclude_prefixes(["[수주:aaa11111] "])
    assert got == ["[수주:aaa11111] ", "[수주:bbb22222] "]   # CLI 우선, 중복 제거


def test_env_unset_is_no_filter(monkeypatch):
    monkeypatch.delenv("WATCHER_EXCLUDE_PREFIXES", raising=False)
    assert linear_watcher.resolve_exclude_prefixes(None) is None
    assert linear_watcher.resolve_exclude_prefixes([]) is None


def test_env_empty_string_is_no_filter(monkeypatch):
    """빈 env 는 빈 접두사 하나로 새지 않는다(전체 제외 사고 방지)."""
    monkeypatch.setenv("WATCHER_EXCLUDE_PREFIXES", "")
    assert linear_watcher.resolve_exclude_prefixes(None) is None


def test_env_exclude_reaches_fetch(scratch_paths, monkeypatch):
    """env 만 설정해도 조회 호출까지 전달된다 — cron 라인에서 쓰는 형태."""
    monkeypatch.setenv("WATCHER_EXCLUDE_PREFIXES", "[수주:aaa11111] ")
    with patch.object(
        linear_watcher, "fetch_queued_issues", return_value=NODES[:1]
    ) as fetch:
        _run_main(["--dry-run"])

    _, kwargs = fetch.call_args
    assert kwargs["exclude_prefixes"] == ["[수주:aaa11111] "]


if __name__ == "__main__":
    # 직접 실행(`python test_...py`)해도 수집·실행되게 한다 — 아무 것도 하지 않고
    # 종료코드 0 을 내는 "거짓 초록"을 막기 위함.
    raise SystemExit(pytest.main([__file__]))
