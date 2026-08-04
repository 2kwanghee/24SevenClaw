"""webhook_server 재트리거 체인 제어 단위 테스트 (CE-349).

실측 결함: 잔여 Queued 이슈가 있는데 파이프라인이 파일락에 걸려 SKIP 으로 끝나면
`_check_and_retrigger` 가 6초 주기로 무한 재기동했다(진척 0 busy loop).

커버:
  - 잔여 이슈 없음(watcher exit != 0) → IDLE, 재트리거 없음, 체인 카운터 0
  - 잔여 이슈 있음 + 파일락 보유자 생존 → STOP-CHAIN, 재트리거 없음 (핵심 회귀)
  - 잔여 이슈 있음 + 잔류 락(보유자 종료) → 정상 재트리거 (회귀 0 확인)
  - 잔여 이슈 있음 + 락 없음 → 연속 재트리거가 MAX_RETRIGGER_CHAIN 에서 멈춤
  - reset_retrigger_chain() → 새 이벤트에 예산 복원
  - _live_lock_holder: 락 없음 / 깨진 내용 / 자기 PID / 생존 PID

Usage:
    cd ClickEye && pytest scripts/tests/test_webhook_retrigger.py -v
"""
from __future__ import annotations

import os
import sys

import pytest

# scripts/ 를 import path 에 추가(webhook_server import 용).
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import webhook_server as ws  # noqa: E402


class _Res:
    """subprocess.run 반환 대역 — returncode 만 쓴다."""

    def __init__(self, returncode: int):
        self.returncode = returncode


@pytest.fixture
def harness(monkeypatch, tmp_path):
    """watcher 판정·재트리거·sleep·락 경로를 전부 대역으로 교체한 하네스.

    반환 dict:
      set_watcher(rc)   watcher exit code 지정(0 = 잔여 이슈 있음)
      set_lock(text)    락 파일 내용 지정(None = 락 파일 없음)
      triggers          trigger_pipeline 호출 횟수(list 길이)
      logs              수집된 로그 문자열
    """
    state = {"watcher_rc": 0, "triggers": [], "logs": []}
    lock_file = tmp_path / ".pipeline_lock"

    monkeypatch.setattr(ws, "PIPELINE_LOCK_FILE", str(lock_file))
    monkeypatch.setattr(ws, "_retrigger_chain", 0, raising=False)
    monkeypatch.setattr(ws, "subprocess", _FakeSubprocess(state))
    monkeypatch.setattr(ws, "trigger_pipeline", lambda: state["triggers"].append(1))
    monkeypatch.setattr(ws.time, "sleep", lambda _s: None)  # 5초 대기 제거
    monkeypatch.setattr(ws, "log", lambda m: state["logs"].append(m))

    def set_lock(text):
        if text is None:
            if lock_file.exists():
                lock_file.unlink()
        else:
            lock_file.write_text(text)

    def set_watcher(rc):
        state["watcher_rc"] = rc

    return {
        "set_watcher": set_watcher,
        "set_lock": set_lock,
        "state": state,
        "lock_file": lock_file,
    }


class _FakeSubprocess:
    """ws.subprocess 대역 — run 만 흉내내고 실제 watcher 를 실행하지 않는다."""

    def __init__(self, state):
        self._state = state

    def run(self, *_a, **_kw):
        return _Res(self._state["watcher_rc"])


def _joined(logs):
    return "\n".join(logs)


# ── _live_lock_holder ────────────────────────────────────────────────────────


def test_lock_holder_none_when_no_file(harness):
    harness["set_lock"](None)
    assert ws._live_lock_holder() is None


def test_lock_holder_none_when_garbage(harness):
    harness["set_lock"]("not-a-pid")
    assert ws._live_lock_holder() is None


def test_lock_holder_ignores_own_pid(harness):
    """자기 PID 는 보유자로 보지 않는다(자기 자신 때문에 체인이 끊기면 안 됨)."""
    harness["set_lock"](str(os.getpid()))
    assert ws._live_lock_holder() is None


def test_lock_holder_detects_live_process(harness):
    """살아있는 타 PID(=PID 1, 항상 존재) 는 보유자로 판정."""
    harness["set_lock"]("1")
    assert ws._live_lock_holder() == 1


def test_lock_holder_none_when_stale(harness):
    """종료된 PID 의 잔류 락은 보유자 아님 — 다음 실행이 스스로 제거한다."""
    dead = _find_dead_pid()
    harness["set_lock"](str(dead))
    assert ws._live_lock_holder() is None


def _find_dead_pid() -> int:
    """존재하지 않는 PID 하나 찾기."""
    for candidate in range(4_000_000, 4_000_100):
        try:
            os.kill(candidate, 0)
        except ProcessLookupError:
            return candidate
        except OSError:
            continue
    pytest.skip("사용 가능한 종료 PID 를 찾지 못함")


# ── _check_and_retrigger ─────────────────────────────────────────────────────


def test_idle_when_no_remaining_issue(harness):
    harness["set_watcher"](2)   # 잔여 이슈 없음
    harness["set_lock"](None)
    ws._check_and_retrigger()
    assert harness["state"]["triggers"] == []
    assert "IDLE" in _joined(harness["state"]["logs"])
    assert ws._retrigger_chain == 0


def test_stop_chain_when_lock_holder_alive(harness):
    """핵심 회귀: 잔여 이슈 + 락 보유자 생존 → 재트리거 금지."""
    harness["set_watcher"](0)   # 잔여 이슈 있음
    harness["set_lock"]("1")    # PID 1 = 생존
    ws._check_and_retrigger()
    assert harness["state"]["triggers"] == []
    logs = _joined(harness["state"]["logs"])
    assert "STOP-CHAIN" in logs
    assert "RE-TRIGGER" not in logs


def test_retrigger_when_lock_is_stale(harness):
    """회귀 0: 잔류 락뿐이면 기존 재트리거 동작을 유지한다."""
    harness["set_watcher"](0)
    harness["set_lock"](str(_find_dead_pid()))
    ws._check_and_retrigger()
    assert harness["state"]["triggers"] == [1]
    assert "RE-TRIGGER" in _joined(harness["state"]["logs"])


def test_retrigger_chain_is_capped(harness, monkeypatch):
    """락이 없어도(다른 원인으로 진척 0) 연속 체인은 상한에서 끊긴다."""
    harness["set_watcher"](0)
    harness["set_lock"](None)

    # trigger_pipeline 이 체인을 재귀 호출하는 실제 구조를 모사:
    # _reap → _check_and_retrigger. 상한이 없으면 무한 재귀가 된다.
    def _recursive_trigger():
        harness["state"]["triggers"].append(1)
        ws._check_and_retrigger()

    monkeypatch.setattr(ws, "trigger_pipeline", _recursive_trigger)

    ws._check_and_retrigger()

    assert len(harness["state"]["triggers"]) == ws.MAX_RETRIGGER_CHAIN
    logs = _joined(harness["state"]["logs"])
    assert f"상한 {ws.MAX_RETRIGGER_CHAIN}회 도달" in logs
    assert ws._retrigger_chain == 0   # 중단 시 예산 복원


def test_reset_restores_budget(harness):
    """새 이벤트/새 job 은 full 예산으로 시작한다."""
    harness["set_watcher"](0)
    harness["set_lock"](None)
    ws._check_and_retrigger()          # 체인 1 소비
    assert ws._retrigger_chain == 1
    ws.reset_retrigger_chain()
    assert ws._retrigger_chain == 0


def test_watcher_failure_does_not_raise(harness, monkeypatch):
    """watcher 호출 자체가 터져도 워커를 죽이지 않는다(기존 계약 유지)."""

    class _Boom:
        def run(self, *_a, **_kw):
            raise OSError("boom")

    monkeypatch.setattr(ws, "subprocess", _Boom())
    ws._check_and_retrigger()
    assert "WARN" in _joined(harness["state"]["logs"])
    assert harness["state"]["triggers"] == []
