"""webhook_worker(호스트 실행 워커) 단위 테스트.

실제 Redis·실제 파이프라인 실행 없이(monkeypatch/fake) 워커 견고성을 검증한다.
plan 2·3단계 검증(--once 빈 큐 exit 0, dispatch 라우팅, 재적재)과 확정 결함
no 5·7·8·9·11 의 회귀 방지를 겸한다.

커버:
  - 빈 큐 --once → exit 0
  - 잘못된 JSON job → 죽지 않고 소비 후 진행(no 11)
  - 미지원 kind → 로그 후 스킵(어떤 trigger 도 호출 안 됨)
  - kind 별 디스패치 라우팅(pipeline / confirmer)
  - trigger_pipeline False(미점화) → 재시도 후 job 재적재(no 7)
  - Redis 연결 오류(ConnectionError) → _CONN_ERROR 신호 + 상시 루프 백오프 재접속 생존(no 5)
  - _enqueue_job(수신전용) → 큐 계약 스키마로 RPUSH

Usage:
    cd ClickEye && pytest scripts/tests/test_webhook_worker.py -v
"""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import Mock

import pytest

# scripts/ 를 import path 에 추가(webhook_worker / webhook_server import 용).
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import redis  # noqa: E402
import webhook_server  # noqa: E402
import webhook_worker as w  # noqa: E402


# ── Fake Redis (실제 네트워크 없음) ───────────────────────────────────────────


class FakeRedis:
    """blpop/rpush/ping 만 흉내내는 인메모리 대역."""

    def __init__(self, items=None, blpop_exc=None):
        # items: BLPOP 이 순서대로 돌려줄 raw(bytes) 목록
        self.items = list(items or [])
        self.blpop_exc = blpop_exc
        self.rpushed: list[tuple] = []  # (key, value) 기록
        self.blpop_calls = 0

    def blpop(self, key, timeout=0):
        self.blpop_calls += 1
        if self.blpop_exc is not None:
            raise self.blpop_exc
        if self.items:
            return (key if isinstance(key, bytes) else str(key).encode(), self.items.pop(0))
        return None  # 빈 큐(timeout)

    def rpush(self, key, value):
        self.rpushed.append((key, value))
        return len(self.rpushed)

    def ping(self):
        return True


def _job_bytes(kind="pipeline", identifier="CE-1", state="DayQueued") -> bytes:
    return json.dumps(
        {
            "kind": kind,
            "identifier": identifier,
            "state": state,
            "received_at": "2026-07-30T00:00:00Z",
        }
    ).encode()


@pytest.fixture(autouse=True)
def _no_delays(monkeypatch):
    """모든 테스트에서 sleep·idle 대기를 무력화(지연 제거, 실 파이프라인 미접촉)."""
    monkeypatch.setattr(w.time, "sleep", lambda *a, **k: None)
    monkeypatch.setattr(w, "_wait_pipeline_idle", lambda *a, **k: None)


# ── _process_one: 빈 큐 / JSON / kind ─────────────────────────────────────────


def test_process_one_empty_queue_returns_empty():
    """빈 큐(blpop None) → _EMPTY 신호(--once 정상 종료 경로)."""
    client = FakeRedis(items=[])
    assert w._process_one(client, block=False) is w._EMPTY


def test_process_one_bad_json_consumed_not_crash():
    """잘못된 JSON → 예외 없이 True(1건 소비) 반환(워커 생존)."""
    client = FakeRedis(items=[b"{not valid json"])
    assert w._process_one(client, block=False) is True


def test_process_one_unsupported_kind_skipped(monkeypatch):
    """미지원 kind → 로그 후 스킵, 어떤 trigger 도 호출되지 않음."""
    tp, tc = Mock(return_value=True), Mock(return_value=True)
    monkeypatch.setattr(w, "trigger_pipeline", tp)
    monkeypatch.setattr(w, "trigger_confirmer", tc)
    client = FakeRedis(items=[_job_bytes(kind="unknown")])
    assert w._process_one(client, block=False) is True
    tp.assert_not_called()
    tc.assert_not_called()


# ── dispatch 라우팅 ───────────────────────────────────────────────────────────


def test_dispatch_routes_pipeline(monkeypatch):
    """kind=pipeline → trigger_pipeline 만 호출(True=DRY_RUN 취급으로 즉시 반환)."""
    tp, tc = Mock(return_value=True), Mock(return_value=True)
    monkeypatch.setattr(w, "trigger_pipeline", tp)
    monkeypatch.setattr(w, "trigger_confirmer", tc)
    client = FakeRedis(items=[_job_bytes(kind="pipeline")])
    assert w._process_one(client, block=False) is True
    tp.assert_called_once()
    tc.assert_not_called()


def test_dispatch_routes_confirmer(monkeypatch):
    """kind=confirmer → trigger_confirmer 만 호출."""
    tp, tc = Mock(return_value=True), Mock(return_value=True)
    monkeypatch.setattr(w, "trigger_pipeline", tp)
    monkeypatch.setattr(w, "trigger_confirmer", tc)
    client = FakeRedis(items=[_job_bytes(kind="confirmer")])
    assert w._process_one(client, block=False) is True
    tc.assert_called_once()
    tp.assert_not_called()


def test_pipeline_missfire_requeues_job(monkeypatch):
    """trigger_pipeline 이 계속 False(미점화) → 재시도 1회 후 최종 실패 시 job 재적재(no 7)."""
    tp = Mock(return_value=False)  # 항상 미점화
    monkeypatch.setattr(w, "trigger_pipeline", tp)
    client = FakeRedis(items=[_job_bytes(kind="pipeline", identifier="CE-77")])
    assert w._process_one(client, block=False) is True
    assert tp.call_count == 2  # 초기 + idle 대기 후 재시도
    assert len(client.rpushed) == 1  # 재적재(유실 방지)
    key, val = client.rpushed[0]
    assert key == w.QUEUE_KEY
    assert json.loads(val)["identifier"] == "CE-77"


# ── Redis 연결 오류(no 5) ─────────────────────────────────────────────────────


def test_process_one_connection_error_returns_signal():
    """blpop 중 ConnectionError → 예외 전파 없이 _CONN_ERROR 신호 반환."""
    client = FakeRedis(blpop_exc=redis.exceptions.ConnectionError("down"))
    assert w._process_one(client, block=False) is w._CONN_ERROR


def test_get_redis_missing_package_returns_none(monkeypatch):
    """redis 패키지 미설치 + exit_on_fail=False(재접속 경로) → exit 없이 None."""
    monkeypatch.setattr(w, "redis", None)
    assert w._get_redis(exit_on_fail=False) is None


# ── main(): --once ────────────────────────────────────────────────────────────


def test_once_empty_exits_zero(monkeypatch):
    """--once 빈 큐 → exit 0(에러 아님)."""
    monkeypatch.setattr(w, "_get_redis", lambda *a, **k: FakeRedis(items=[]))
    monkeypatch.setattr(sys, "argv", ["webhook_worker.py", "--once"])
    with pytest.raises(SystemExit) as ei:
        w.main()
    assert ei.value.code == 0


def test_once_connection_error_exits_four(monkeypatch):
    """--once 연결 오류 → exit 4(다음 cron 이 재시도)."""
    monkeypatch.setattr(
        w, "_get_redis", lambda *a, **k: FakeRedis(blpop_exc=redis.exceptions.ConnectionError("x"))
    )
    monkeypatch.setattr(sys, "argv", ["webhook_worker.py", "--once"])
    with pytest.raises(SystemExit) as ei:
        w.main()
    assert ei.value.code == 4


def test_once_processes_one_pipeline(monkeypatch):
    """--once 로 큐의 pipeline job 1건 처리 후 exit 0."""
    tp = Mock(return_value=True)
    monkeypatch.setattr(w, "trigger_pipeline", tp)
    monkeypatch.setattr(w, "_get_redis", lambda *a, **k: FakeRedis(items=[_job_bytes()]))
    monkeypatch.setattr(sys, "argv", ["webhook_worker.py", "--once"])
    with pytest.raises(SystemExit) as ei:
        w.main()
    assert ei.value.code == 0
    tp.assert_called_once()


# ── main(): 상시 루프 백오프 재접속 생존(no 5) ────────────────────────────────


def test_loop_reconnects_after_connection_error(monkeypatch):
    """연결 오류 발생 → 백오프 후 재접속하고 프로세스가 죽지 않는다."""
    reconnects = {"count": 0}
    calls = {"n": 0}

    def fake_get(exit_on_fail=True):
        reconnects["count"] += 1
        return FakeRedis(items=[])

    def fake_process(client, block):
        calls["n"] += 1
        if calls["n"] == 1:
            return w._CONN_ERROR  # 첫 회 연결 오류
        raise KeyboardInterrupt  # 재접속 후 정상 루프 → 종료로 테스트 탈출

    monkeypatch.setattr(w, "_get_redis", fake_get)
    monkeypatch.setattr(w, "_process_one", fake_process)
    monkeypatch.setattr(sys, "argv", ["webhook_worker.py"])

    w.main()  # KeyboardInterrupt 캐치 → 예외 없이 반환(프로세스 생존 확인)

    assert reconnects["count"] >= 2  # 최초 확보 + 재접속 1회
    assert calls["n"] == 2


# ── webhook_server 수신전용 모드: _enqueue_job 큐 계약 ────────────────────────


def test_enqueue_job_rpushes_contract_schema(monkeypatch):
    """_enqueue_job 이 QUEUE_KEY 에 계약 스키마(kind/identifier/state/received_at)로 RPUSH."""
    fake = FakeRedis()
    monkeypatch.setattr(webhook_server, "_get_queue_client", lambda: fake)
    webhook_server._enqueue_job("pipeline", "CE-338", "DayQueued")
    assert len(fake.rpushed) == 1
    key, val = fake.rpushed[0]
    assert key == webhook_server.QUEUE_KEY
    job = json.loads(val)
    assert job["kind"] == "pipeline"
    assert job["identifier"] == "CE-338"
    assert job["state"] == "DayQueued"
    assert "received_at" in job
