"""완주 오케스트레이터 재시도 원장 테스트 (P1, D-13).

검증 축:
  1. exit 계약 — record-failure 가 한도 미만이면 0, 도달하면 3. 파이프라인 셸이 이 코드로
     분기하므로(0→Queued 복귀, 3→Backlog+정지) 이 계약이 깨지면 티켓이 잘못된 상태로 간다.
  2. 한도 전이 — 정확히 limit 회째에 터미널. CLI --limit > env > 기본 3 우선순위.
  3. 영속성 — 프로세스(호출)를 넘어 카운트가 생존한다(재개 가능성의 근거).
  4. 원장 파손 — 깨진 JSON 은 빈 원장으로 복구하되 **stderr 경고 필수**(조용한 초기화 금지 —
     이력 유실은 한도 리셋이므로 관측돼야 한다).
  5. clear/status — 성공 정리와 정지 보고 스키마.

Usage:
    cd ClickEye && pytest scripts/tests/test_retry_ledger.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import retry_ledger as rl  # noqa: E402

_CLI = os.path.join(_SCRIPTS_DIR, "retry_ledger.py")


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv(rl.LIMIT_ENV, raising=False)
    yield


def _cli(tmp_path, *args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, _CLI, "--project-dir", str(tmp_path), *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ── 1. exit 계약 (CLI subprocess — 셸이 소비하는 실제 인터페이스) ────────────


def test_cli_exit_contract_retry_then_terminal(tmp_path):
    """기본 한도 3: 1·2회 실패는 exit 0(재시도), 3회째 exit 3(터미널)."""
    for i in (1, 2):
        r = _cli(tmp_path, "record-failure", "--issue", "CE-1", "--reason", f"실패{i}")
        assert r.returncode == rl.EXIT_RETRY, r.stdout + r.stderr
        assert "RETRY" in r.stdout
    r = _cli(tmp_path, "record-failure", "--issue", "CE-1", "--reason", "실패3")
    assert r.returncode == rl.EXIT_TERMINAL, r.stdout + r.stderr
    assert "TERMINAL" in r.stdout


def test_cli_exit_contract_other_commands_zero(tmp_path):
    assert _cli(tmp_path, "clear", "--issue", "CE-9").returncode == 0
    assert _cli(tmp_path, "status").returncode == 0
    assert _cli(tmp_path, "status", "--json").returncode == 0
    assert _cli(tmp_path, "reset").returncode == 0


# ── 2. 한도 해석 우선순위 ────────────────────────────────────────────────────


def test_limit_priority_cli_over_env_over_default(monkeypatch):
    assert rl.resolve_limit(5) == 5  # CLI 명시가 최우선
    monkeypatch.setenv(rl.LIMIT_ENV, "7")
    assert rl.resolve_limit(None) == 7  # env
    assert rl.resolve_limit(2) == 2  # CLI 가 env 도 이긴다
    monkeypatch.delenv(rl.LIMIT_ENV)
    assert rl.resolve_limit(None) == rl.DEFAULT_LIMIT  # 기본 3


@pytest.mark.parametrize("bad", ["abc", "0", "-1", "  ", "1.5"])
def test_limit_env_invalid_falls_back_to_default(monkeypatch, bad):
    """env 파싱 불가/0 이하는 조용히 기본값 — 원장이 한도 0 으로 즉시 터미널 나는 것 방지."""
    monkeypatch.setenv(rl.LIMIT_ENV, bad)
    assert rl.resolve_limit(None) == rl.DEFAULT_LIMIT


def test_cli_limit_one_is_immediately_terminal(tmp_path):
    r = _cli(tmp_path, "record-failure", "--issue", "CE-2", "--reason", "x", "--limit", "1")
    assert r.returncode == rl.EXIT_TERMINAL


def test_env_limit_respected_via_cli(tmp_path):
    env = {rl.LIMIT_ENV: "2"}
    r1 = _cli(tmp_path, "record-failure", "--issue", "CE-3", "--reason", "x", env_extra=env)
    r2 = _cli(tmp_path, "record-failure", "--issue", "CE-3", "--reason", "x", env_extra=env)
    assert (r1.returncode, r2.returncode) == (rl.EXIT_RETRY, rl.EXIT_TERMINAL)


# ── 3. 영속성 · 원장 내용 ────────────────────────────────────────────────────


def test_counts_survive_across_processes(tmp_path):
    """호출(프로세스)마다 원장을 다시 읽어도 카운트가 이어진다 — 재개 가능성의 근거."""
    _cli(tmp_path, "record-failure", "--issue", "CE-4", "--reason", "1차")
    ledger = rl.load(str(tmp_path))
    assert ledger["CE-4"]["attempts"] == 1
    assert ledger["CE-4"]["terminal"] is False

    _cli(tmp_path, "record-failure", "--issue", "CE-4", "--reason", "2차")
    ledger = rl.load(str(tmp_path))
    assert ledger["CE-4"]["attempts"] == 2
    assert ledger["CE-4"]["last_reason"] == "2차"
    assert ledger["CE-4"]["first_failed_at"] <= ledger["CE-4"]["last_failed_at"]


def test_issues_are_independent(tmp_path):
    """한 이슈의 터미널이 다른 이슈의 카운트에 영향을 주지 않는다."""
    for _ in range(3):
        _cli(tmp_path, "record-failure", "--issue", "CE-5", "--reason", "x")
    r = _cli(tmp_path, "record-failure", "--issue", "CE-6", "--reason", "y")
    assert r.returncode == rl.EXIT_RETRY
    ledger = rl.load(str(tmp_path))
    assert ledger["CE-5"]["terminal"] is True
    assert ledger["CE-6"]["terminal"] is False


def test_ledger_file_location_and_atomic_write(tmp_path):
    """원장은 .ralph/retry_ledger.json 에 있고, 쓰기 후 임시 파일이 남지 않는다."""
    rl.record_failure(str(tmp_path), "CE-7", "x", 3)
    path = tmp_path / ".ralph" / "retry_ledger.json"
    assert path.is_file()
    leftovers = [f for f in os.listdir(path.parent) if f.startswith(".retry_ledger.")]
    assert leftovers == [], f"원자적 쓰기 임시파일 잔존: {leftovers}"
    # 저장 내용이 유효 JSON
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["CE-7"]["attempts"] == 1


# ── 4. 원장 파손 — 조용한 초기화 금지 ────────────────────────────────────────


def test_corrupted_ledger_recovers_with_warning(tmp_path, capsys):
    """깨진 JSON → 빈 원장 복구 + stderr 경고. 경고 없는 복구는 무한 재시도로 이어진다."""
    ralph = tmp_path / ".ralph"
    ralph.mkdir()
    (ralph / "retry_ledger.json").write_text("{깨진 json", encoding="utf-8")

    ledger = rl.load(str(tmp_path))
    assert ledger == {}
    err = capsys.readouterr().err
    assert "원장 파손" in err

    # 파손 후에도 record-failure 는 정상 동작(1회차부터 다시)
    rc = rl.record_failure(str(tmp_path), "CE-8", "x", 3)
    assert rc == rl.EXIT_RETRY


def test_non_dict_ledger_recovers_with_warning(tmp_path, capsys):
    ralph = tmp_path / ".ralph"
    ralph.mkdir()
    (ralph / "retry_ledger.json").write_text("[1,2,3]", encoding="utf-8")
    assert rl.load(str(tmp_path)) == {}
    assert "형식 불량" in capsys.readouterr().err


def test_corrupt_entry_value_does_not_crash(tmp_path):
    """이슈 항목 값이 dict 가 아니어도(수동 편집 등) record/status 가 죽지 않는다."""
    ralph = tmp_path / ".ralph"
    ralph.mkdir()
    (ralph / "retry_ledger.json").write_text('{"CE-9": "oops"}', encoding="utf-8")
    rc = rl.record_failure(str(tmp_path), "CE-9", "x", 3)
    assert rc == rl.EXIT_RETRY  # 새 항목으로 재시작(1회차)
    assert rl.load(str(tmp_path))["CE-9"]["attempts"] == 1
    assert rl.status(str(tmp_path), as_json=True) == 0


# ── 5. clear / status ───────────────────────────────────────────────────────


def test_clear_removes_history_so_next_failure_is_fresh(tmp_path):
    """성공 후 clear → 다음 실패는 1회차부터 (누적 이월 금지)."""
    _cli(tmp_path, "record-failure", "--issue", "CE-10", "--reason", "x")
    _cli(tmp_path, "record-failure", "--issue", "CE-10", "--reason", "x")
    _cli(tmp_path, "clear", "--issue", "CE-10")
    assert "CE-10" not in rl.load(str(tmp_path))
    r = _cli(tmp_path, "record-failure", "--issue", "CE-10", "--reason", "x")
    assert r.returncode == rl.EXIT_RETRY
    assert rl.load(str(tmp_path))["CE-10"]["attempts"] == 1


def test_clear_unknown_issue_is_noop_success(tmp_path):
    assert _cli(tmp_path, "clear", "--issue", "NOPE-1").returncode == 0


def test_status_json_schema_splits_terminal_and_retrying(tmp_path):
    """정지 보고가 소비하는 스키마: {terminal: {...}, retrying: {...}}."""
    _cli(tmp_path, "record-failure", "--issue", "CE-11", "--reason", "x")  # retrying
    for _ in range(3):
        _cli(tmp_path, "record-failure", "--issue", "CE-12", "--reason", "y")  # terminal

    r = _cli(tmp_path, "status", "--json")
    data = json.loads(r.stdout)
    assert set(data.keys()) == {"terminal", "retrying"}
    assert "CE-12" in data["terminal"] and "CE-11" in data["retrying"]
    assert data["terminal"]["CE-12"]["attempts"] == 3
    assert data["terminal"]["CE-12"]["last_reason"] == "y"


def test_status_human_readable_mentions_halt(tmp_path):
    for _ in range(3):
        _cli(tmp_path, "record-failure", "--issue", "CE-13", "--reason", "z")
    r = _cli(tmp_path, "status")
    assert "터미널" in r.stdout and "CE-13" in r.stdout


def test_reset_empties_ledger(tmp_path):
    _cli(tmp_path, "record-failure", "--issue", "CE-14", "--reason", "x")
    _cli(tmp_path, "reset")
    assert rl.load(str(tmp_path)) == {}
