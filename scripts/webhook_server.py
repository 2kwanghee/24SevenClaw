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
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
from linear_client import PROJECT_DIR

# ── 설정 ──
DEFAULT_PORT = 9876
DRY_RUN = False
WEBHOOK_SECRET = None

# 중복 실행 방지
_pipeline_lock = threading.Lock()
_last_trigger_time = 0
MIN_TRIGGER_INTERVAL = 5  # 최소 5초 간격 (메모리 lock이 파이프라인 수명과 동기화됨)


def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Linear webhook 서명 검증."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _check_and_retrigger():
    """파이프라인 완료 후 잔여 DayQueued/NightQueued 이슈 확인 → 재트리거."""
    try:
        result = subprocess.run(
            ["python3", "scripts/linear_watcher.py", "--dry-run", "--limit", "1"],
            capture_output=True, text=True, cwd=PROJECT_DIR,
        )
        if result.returncode == 0:  # DayQueued/NightQueued 이슈 존재
            log("RE-TRIGGER: 잔여 DayQueued/NightQueued 이슈 감지 → 재트리거")
            time.sleep(5)
            trigger_pipeline()
        else:
            log("IDLE: 잔여 DayQueued/NightQueued 이슈 없음")
    except Exception as e:
        log(f"WARN: 재트리거 확인 실패: {e}")


def trigger_pipeline():
    """auto_dev_pipeline.sh를 백그라운드로 실행.

    메모리 lock(_pipeline_lock)을 파이프라인 수명과 동기화:
    - acquire: 트리거 시점
    - release: 파이프라인 프로세스 종료 시 (_reap 스레드에서)
    """
    global _last_trigger_time

    if not _pipeline_lock.acquire(blocking=False):
        log("SKIP: 파이프라인 이미 실행 중")
        return

    started = False
    try:
        now = time.time()
        if now - _last_trigger_time < MIN_TRIGGER_INTERVAL:
            log(f"SKIP: 최소 간격 미도달 ({MIN_TRIGGER_INTERVAL}초)")
            return

        _last_trigger_time = now
        pipeline_path = os.path.join(PROJECT_DIR, "scripts", "auto_dev_pipeline.sh")

        if DRY_RUN:
            log("DRY-RUN: 파이프라인 트리거 (실행 안 함)")
            return

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

    finally:
        if not started:
            _pipeline_lock.release()


def trigger_confirmer():
    """linear_confirmer.py를 백그라운드로 실행."""
    confirmer_path = os.path.join(PROJECT_DIR, "scripts", "linear_confirmer.py")

    if DRY_RUN:
        log("DRY-RUN: confirmer 트리거 (실행 안 함)")
        return

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
            self._respond(200, {"status": "ok", "dry_run": DRY_RUN})
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
            log(f"{state_name.upper()}: {identifier} — 파이프라인 트리거")
            thread = threading.Thread(target=trigger_pipeline, daemon=True)
            thread.start()
        elif state_name == "Confirm" and action == "update":
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
