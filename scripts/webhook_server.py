#!/usr/bin/env python3
"""Linear Webhook 수신 서버.

Linear에서 이슈 상태가 Queued로 변경되면 auto_dev_pipeline.sh를 자동 트리거한다.

Usage:
  python3 scripts/webhook_server.py                    # 기본 포트 9876
  python3 scripts/webhook_server.py --port 8080        # 포트 지정
  python3 scripts/webhook_server.py --dry-run           # 파이프라인 실행 안 함 (로그만)

Linear Webhook 설정:
  1. Linear Settings → API → Webhooks → New webhook
  2. URL: http://<서버IP>:9876/webhook/linear
  3. Events: "Issue" 체크
  4. 저장 후 Signing Secret을 WEBHOOK_SECRET 환경변수에 설정

보안:
  - WEBHOOK_SECRET 설정 시 Linear 서명 검증
  - /health 엔드포인트로 상태 확인 가능
"""

import hashlib
import hmac
import json
import os
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(__file__))
from linear_client import PROJECT_DIR

# ── 설정 ──
DEFAULT_PORT = 9876
DRY_RUN = False
WEBHOOK_SECRET = None

# ── 수신전용(enqueue-only) 모드 ──
# WEBHOOK_ENQUEUE_ONLY=true 면 _handle_event 가 trigger_* 대신 Redis 큐에 적재만 한다.
# (컨테이너 수신부에서 사용 — 실행은 호스트 워커가 큐를 소비해 수행)
# 미설정/false 면 기존 동작 그대로(호스트에서 직접 exec) — 하위호환 보장.
ENQUEUE_ONLY = os.getenv("WEBHOOK_ENQUEUE_ONLY", "").strip().lower() in ("true", "1", "on", "yes")
# 큐 계약(두 트랙 공유): 키 clickeye:webhook:jobs (LIST), RPUSH 적재 / BLPOP 소비(FIFO).
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = "clickeye:webhook:jobs"
# 수신전용 모드에서 재사용하는 Redis 클라이언트(이벤트마다 새 커넥션 풀 생성 방지).
_redis_client = None

# 중복 실행 방지
_pipeline_lock = threading.Lock()
_last_trigger_time = 0
MIN_TRIGGER_INTERVAL = 5  # 최소 5초 간격 (메모리 lock이 파이프라인 수명과 동기화됨)

# ── 재트리거 체인 제어 (CE-349) ──
# 잔여 Queued 이슈가 있어도 파이프라인이 그것을 "소비할 수 없는" 상태면 재트리거는
# 진척 없는 busy loop 가 된다(실측: 파일락 SKIP 시 6초 주기 무한 스핀). 두 겹으로 끊는다.
#   ① 파일락 생존 판정 — 직전 실행이 SKIP 으로 끝났음을 확정 신호로 감지(즉시 중단)
#   ② 연속 체인 상한 — 락 외 원인(시트 disabled, 제외 접두사 불일치 등)의 안전망
# 중단 후 복구는 폴링 cron(auto_dev_pipeline.sh --once)이 담당한다.
MAX_RETRIGGER_CHAIN = 5
_retrigger_chain = 0
# auto_dev_pipeline.sh:32 의 LOCK_FILE 과 동일 경로. 전용 러너의 키별 락
# (.pipeline_lock.<KEY>)은 웹훅이 띄우는 기본 러너를 막지 않으므로 기본 락만 본다.
PIPELINE_LOCK_FILE = os.path.join(PROJECT_DIR, ".ralph", ".pipeline_lock")


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Linear webhook 서명 검증."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def reset_retrigger_chain():
    """새 외부 이벤트 처리 시작 시 재트리거 체인 예산을 되돌린다(CE-349).

    상한은 "한 이벤트에서 파생된 연속 체인"에 걸린다. 새로 도착한 이벤트는 별개의
    작업이므로 예산을 full 로 돌려주지 않으면 이전 체인의 잔여가 새 이벤트를 굶긴다.
    호출부: _handle_event(직접 실행 경로) / webhook_worker(큐 소비 경로).
    """
    global _retrigger_chain
    _retrigger_chain = 0


def _live_lock_holder():
    """파이프라인 파일락을 잡고 있는 살아있는 타 프로세스 PID(없으면 None) — CE-349.

    auto_dev_pipeline.sh 는 정상 종료 시 trap cleanup 으로 락을 지운다. 따라서 재트리거
    판정 시점에 락 파일이 남아 있고 그 PID 가 살아 있다면, 직전 실행은 그 락에 걸려
    "SKIP: 이전 파이프라인 실행 중" 으로 끝났다는 뜻이다(= 진척 0). 이 상태에서 재트리거
    하면 락 보유자가 끝날 때까지 무한 스핀한다.
    """
    try:
        with open(PIPELINE_LOCK_FILE) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None          # 락 없음 or 판독 불가 → 판정 보류(체인 상한이 안전망)
    if pid <= 0 or pid == os.getpid():
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None          # 잔류 락(보유자 이미 종료) — 다음 실행이 스스로 제거한다
    except PermissionError:
        return pid           # 타 사용자 소유이지만 생존
    except OSError:
        return None
    return pid


def _check_and_retrigger():
    """파이프라인 완료 후 잔여 DayQueued/NightQueued 이슈 확인 → 재트리거.

    재트리거는 "직전 실행이 실제로 진척을 만들었을 때"만 의미가 있다. 진척 없는
    재트리거를 두 겹으로 차단한다(CE-349 — 상세 근거는 MAX_RETRIGGER_CHAIN 주석).
    """
    global _retrigger_chain
    try:
        result = subprocess.run(
            ["python3", "scripts/linear_watcher.py", "--dry-run", "--limit", "1"],
            capture_output=True, text=True, cwd=PROJECT_DIR,
        )
        if result.returncode != 0:
            log("IDLE: 잔여 DayQueued/NightQueued 이슈 없음")
            _retrigger_chain = 0
            return

        # DayQueued/NightQueued 이슈 존재 — 다만 소비 가능한 상태인지 먼저 확인한다.
        holder = _live_lock_holder()
        if holder is not None:
            log(
                f"STOP-CHAIN: 파이프라인 파일락 보유 PID {holder} 생존 — 직전 실행이 "
                "SKIP(진척 0)으로 종료. 재트리거 중단(폴링 cron 이 복구)"
            )
            _retrigger_chain = 0
            return

        if _retrigger_chain >= MAX_RETRIGGER_CHAIN:
            log(
                f"STOP-CHAIN: 연속 재트리거 상한 {MAX_RETRIGGER_CHAIN}회 도달 — "
                "체인 중단(폴링 cron 이 복구)"
            )
            _retrigger_chain = 0
            return

        _retrigger_chain += 1
        log(
            "RE-TRIGGER: 잔여 DayQueued/NightQueued 이슈 감지 → 재트리거 "
            f"({_retrigger_chain}/{MAX_RETRIGGER_CHAIN})"
        )
        time.sleep(5)
        trigger_pipeline()
    except Exception as e:
        log(f"WARN: 재트리거 확인 실패: {e}")


def trigger_pipeline():
    """auto_dev_pipeline.sh를 백그라운드로 실행.

    메모리 lock(_pipeline_lock)을 파이프라인 수명과 동기화:
    - acquire: 트리거 시점
    - release: 파이프라인 프로세스 종료 시 (_reap 스레드에서)
    """
    global _last_trigger_time

    # 반환값(호스트 워커가 순차 제어에 사용 — 기존 스레드 호출부는 반환값 무시로 회귀 0):
    #   Popen  → 실제 파이프라인 프로세스 시작(워커가 .wait() 로 완료 대기)
    #   True   → DRY_RUN(실행 안 함)
    #   False  → 미점화(이미 실행 중 or 최소간격 미도달)
    if not _pipeline_lock.acquire(blocking=False):
        log("SKIP: 파이프라인 이미 실행 중")
        return False

    started = False
    try:
        now = time.time()
        if now - _last_trigger_time < MIN_TRIGGER_INTERVAL:
            log(f"SKIP: 최소 간격 미도달 ({MIN_TRIGGER_INTERVAL}초)")
            return False

        _last_trigger_time = now
        pipeline_path = os.path.join(PROJECT_DIR, "scripts", "auto_dev_pipeline.sh")

        if DRY_RUN:
            log("DRY-RUN: 파이프라인 트리거 (실행 안 함)")
            return True

        log("TRIGGER: auto_dev_pipeline.sh 실행 시작")

        # 로그 파일
        log_dir = os.path.join(PROJECT_DIR, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        lf = open(log_file, "w")
        proc = subprocess.Popen(
            ["bash", pipeline_path],
            stdout=lf, stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
        )

        log(f"STARTED: PID {proc.pid}, 로그: {log_file}")
        started = True

        # 파이프라인 종료 대기 → lock 해제 → 잔여 이슈 재트리거
        def _reap(p, f):
            p.wait()
            f.close()
            log(f"REAPED: PID {p.pid}, exit={p.returncode}")
            _pipeline_lock.release()
            _check_and_retrigger()

        threading.Thread(target=_reap, args=(proc, lf), daemon=True).start()
        return proc

    finally:
        if not started:
            _pipeline_lock.release()


def trigger_confirmer():
    """linear_confirmer.py를 백그라운드로 실행.

    반환값(호스트 워커가 순차 대기에 사용 — 기존 스레드 호출부는 반환값 무시로 회귀 0):
      Popen → confirmer 프로세스 시작(워커가 .wait() 로 완료 대기, 파이프라인과 겹침 방지)
      True  → DRY_RUN(실행 안 함)
    """
    confirmer_path = os.path.join(PROJECT_DIR, "scripts", "linear_confirmer.py")

    if DRY_RUN:
        log("DRY-RUN: confirmer 트리거 (실행 안 함)")
        return True

    log("TRIGGER: linear_confirmer.py 실행 시작")

    log_dir = os.path.join(PROJECT_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "confirmer.log")

    lf = open(log_file, "a")
    lf.write(f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    lf.flush()
    proc = subprocess.Popen(
        ["python3", confirmer_path],
        stdout=lf, stderr=subprocess.STDOUT,
        cwd=PROJECT_DIR,
    )

    log(f"STARTED: confirmer PID {proc.pid}, 로그: {log_file}")

    def _reap(p, f):
        p.wait()
        f.close()
        log(f"REAPED: confirmer PID {p.pid}, exit={p.returncode}")

    threading.Thread(target=_reap, args=(proc, lf), daemon=True).start()
    return proc


def _enqueue_job(kind: str, identifier: str, state_name: str):
    """수신전용 모드: 실행 대신 Redis 큐(clickeye:webhook:jobs)에 job 을 RPUSH 한다.

    - redis 는 지연 import — 수신전용 모드가 아닐 때 redis 미설치 환경에서 죽지 않도록.
    - RPUSH 실패는 삼키지 않고 log() 로 명확히 남기되 예외를 밖으로 던지지 않는다.
      호출부(_handle_event)는 200 을 유지해 Linear 재전송 폭주를 막는다 — 유실된
      트리거는 다음 상태전이/워커 watchdog/폴링 cron 으로 자연 복구된다.
    """
    global _redis_client
    try:
        client = _get_queue_client()
        job = {
            "kind": kind,
            "identifier": identifier,
            "state": state_name,
            "received_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        client.rpush(QUEUE_KEY, json.dumps(job))
        log(f"ENQUEUE: {kind} {identifier} state={state_name} → {QUEUE_KEY}")
    except Exception as e:
        # 접속 예외 시 캐시를 버려 다음 이벤트에서 재생성(끊긴 커넥션 재사용 방지).
        _redis_client = None
        log(f"ERROR: 큐 적재 실패({kind} {identifier} state={state_name}) — {e}")


def _get_queue_client():
    """수신전용 모드용 Redis 클라이언트를 지연 생성·캐시해 재사용한다.

    redis 는 지연 import — 수신전용 모드가 아닐 때 redis 미설치 환경에서 죽지 않도록.
    최초 1회만 from_url 로 생성하고 이후 재사용한다(커넥션 풀 누적 방지). 접속 예외는
    _enqueue_job 이 캐시를 None 으로 리셋해 다음 이벤트에서 재생성한다.
    """
    global _redis_client
    if _redis_client is None:
        import redis  # 지연 import (수신전용 모드에서만 필요)
        _redis_client = redis.from_url(REDIS_URL)
    return _redis_client


def _env_value(key: str) -> str:
    """환경변수 → 루트 .env 순으로 단일 키를 읽는다(미존재 시 빈 문자열)."""
    val = os.getenv(key)
    if val is not None:
        return val
    env_path = os.path.join(PROJECT_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
    return ""


def ingest_to_llm(data: dict, identifier: str, state_name: str):
    """상태전이 이벤트를 clickeye-llm KB 로 머신 인제스트 (P1.6).

    명시적 opt-in: FLOWOPS_LLM_INGEST 미설정/false = off (회귀 0).
    서버(API)가 team_id → project 역매핑을 수행하고, 실패는 log 만 남기고 무시한다
    (웹훅 처리에 절대 영향 없음). source_id=linear:<identifier> — 동일 이슈 재이벤트는
    최신 상태 1문서로 갱신된다(clickeye-llm 선삭제 계약).
    """
    try:
        if _env_value("FLOWOPS_LLM_INGEST").strip().lower() not in ("true", "1", "on", "yes"):
            return
        base_url = _env_value("FLOWOPS_GOVERNANCE_SERVICE_URL").rstrip("/")
        if not base_url:
            return
        # Linear Issue webhook 페이로드의 팀 식별자: data.teamId(현행) → data.team.id(방어).
        team = data.get("team") or {}
        team_id = data.get("teamId") or (team.get("id") if isinstance(team, dict) else None)
        title = data.get("title", "?")
        payload = {
            "team_id": team_id,
            "source_id": f"linear:{identifier}",
            "text": f"[Linear] {identifier} '{title}' → 상태 {state_name}",
            "metadata": {"kind": "linear_webhook", "state": state_name},
        }
        req = urllib.request.Request(
            f"{base_url}/api/v1/llm/ingest/pipeline",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Governance-Token": _env_value("GOVERNANCE_SERVICE_TOKEN"),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            log(f"LLM-INGEST: {identifier} → HTTP {resp.status}")
    except Exception as e:
        log(f"WARN: LLM 인제스트 실패(무시): {e}")


class WebhookHandler(BaseHTTPRequestHandler):
    """Linear Webhook HTTP 핸들러."""

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "dry_run": DRY_RUN, "enqueue_only": ENQUEUE_ONLY})
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/webhook/linear":
            self._respond(404, {"error": "not found"})
            return

        # Body 읽기
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._respond(400, {"error": "empty body"})
            return

        body = self.rfile.read(content_length)

        # 서명 검증
        if WEBHOOK_SECRET:
            signature = self.headers.get("Linear-Signature", "")
            if not verify_signature(body, signature, WEBHOOK_SECRET):
                log("REJECTED: 서명 검증 실패")
                self._respond(401, {"error": "invalid signature"})
                return

        # JSON 파싱
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "invalid json"})
            return

        # 이벤트 처리
        self._handle_event(payload)
        self._respond(200, {"ok": True})

    def _handle_event(self, payload: dict):
        """Linear webhook 이벤트 처리."""
        action = payload.get("action")
        event_type = payload.get("type")
        data = payload.get("data", {})

        # Issue 이벤트만 처리
        if event_type != "Issue":
            log(f"IGNORE: type={event_type}, action={action}")
            return

        identifier = data.get("identifier", "?")
        title = data.get("title", "?")
        state = data.get("state", {})
        state_name = state.get("name", "?") if isinstance(state, dict) else "?"

        log(f"EVENT: {action} {identifier} '{title}' → {state_name}")

        # [P1.6] 상태전이를 KB 로 머신 인제스트 (FLOWOPS_LLM_INGEST opt-in, 비차단 스레드 1회)
        if action in ("create", "update") and state_name != "?":
            threading.Thread(
                target=ingest_to_llm, args=(data, identifier, state_name), daemon=True
            ).start()

        # 상태별 트리거 (DayQueued / NightQueued / Queued 모두 처리)
        if state_name in ("DayQueued", "NightQueued", "Queued") and action in ("update", "create"):
            if ENQUEUE_ONLY:
                # 수신전용: 실행하지 않고 큐에 적재만 한다(호스트 워커가 소비).
                _enqueue_job("pipeline", identifier, state_name)
            else:
                # 기존 경로(회귀 0): 호스트에서 직접 파이프라인 실행.
                log(f"{state_name.upper()}: {identifier} — 파이프라인 트리거")
                reset_retrigger_chain()  # 새 이벤트 = 새 체인 예산 (CE-349)
                thread = threading.Thread(target=trigger_pipeline, daemon=True)
                thread.start()
        elif state_name == "Confirm" and action == "update":
            if ENQUEUE_ONLY:
                _enqueue_job("confirmer", identifier, state_name)
            else:
                log(f"CONFIRM: {identifier} — confirmer 트리거")
                thread = threading.Thread(target=trigger_confirmer, daemon=True)
                thread.start()
        else:
            log(f"SKIP: {identifier} 상태={state_name}")

    def _respond(self, status: int, body: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, format, *args):
        """기본 로그 억제 (자체 로그 사용)."""
        pass


def load_env():
    """Load webhook secret from .env or env vars."""
    global WEBHOOK_SECRET

    secret = os.getenv("WEBHOOK_SECRET")
    if secret:
        WEBHOOK_SECRET = secret
        return

    env_path = os.path.join(PROJECT_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("WEBHOOK_SECRET="):
                    WEBHOOK_SECRET = line.split("=", 1)[1].strip()
                    return


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Linear Webhook 수신 서버")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"포트 (기본: {DEFAULT_PORT})")
    parser.add_argument("--dry-run", action="store_true", help="파이프라인 실행 안 함 (로그만)")
    args = parser.parse_args()

    global DRY_RUN
    DRY_RUN = args.dry_run

    load_env()

    # fail-closed: 수신전용 모드(컨테이너, 공개 노출부)는 HMAC 서명 검증이 유일한
    #   방어선이므로 WEBHOOK_SECRET 이 없으면 기동을 거부한다. 미검증 상태로 인터넷에
    #   노출되면 임의 POST 가 그대로 큐에 적재돼 호스트 파이프라인을 점화할 수 있다.
    #   호스트 단독 모드(ENQUEUE_ONLY 미설정)는 기존 경고만 유지 — 회귀 0.
    if ENQUEUE_ONLY and not WEBHOOK_SECRET:
        log("FATAL: 수신전용 모드는 WEBHOOK_SECRET 필수(공개 노출부) — 기동 거부")
        sys.exit(2)

    server = HTTPServer(("0.0.0.0", args.port), WebhookHandler)
    log(f"Linear Webhook 서버 시작: http://0.0.0.0:{args.port}")
    log(f"  Webhook URL: http://<서버IP>:{args.port}/webhook/linear")
    log(f"  Health check: http://localhost:{args.port}/health")
    log(f"  서명 검증: {'활성' if WEBHOOK_SECRET else '비활성 (WEBHOOK_SECRET 미설정)'}")
    log(f"  Dry-run: {DRY_RUN}")
    log("")
    log("Linear Settings → API → Webhooks 에서 위 URL을 등록하세요.")
    log("Ctrl+C로 종료")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("서버 종료")
        server.server_close()


if __name__ == "__main__":
    main()
