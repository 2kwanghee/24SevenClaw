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
  - WEBHOOK_SECRET_MAP(`teamId=secret` 목록) 설정 시 서명에 성공한 시크릿과 페이로드가
    주장하는 팀의 일치까지 요구 — 타 워크스페이스 시크릿 보유자의 사칭 차단
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
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
from linear_client import PROJECT_DIR

# ── 설정 ──
DEFAULT_PORT = 9876
DRY_RUN = False
WEBHOOK_SECRET = None
# 프로젝트마다 Linear 워크스페이스가 달라 signing secret 도 갈린다. 수신부는 어느
# 워크스페이스가 보낸 요청인지 알 수 없으므로(무 DB 원칙) 후보 시크릿 전부와 대조해
# 하나라도 맞으면 통과시킨다. WEBHOOK_SECRET(단일, 기존) + WEBHOOK_SECRETS(콤마 목록).
WEBHOOK_SECRETS: list[str] = []
# 시크릿 환경변수가 "값과 함께 주어졌는지" — 파싱 결과가 비었을 때 fail-open 을 막는 플래그.
# WEBHOOK_SECRET="   " 처럼 설정은 됐지만 유효 항목이 0개인 경우를 "미설정" 과 구분한다.
# (구코드는 strip 전 값이 truthy 라 검증이 켜져 전부 거부됐다 — 그 fail-closed 를 유지)
WEBHOOK_SECRETS_CONFIGURED = False

# ── 크로스테넌트 바인딩 (WEBHOOK_SECRET_MAP) ──
# 위 후보 목록만으로는 "서명이 맞았다" 가 "그 워크스페이스가 보냈다" 를 뜻하지 않는다.
# A사 시크릿 보유자가 B사 teamId 를 담아 서명하면 통과하고, 이후 귀속은 페이로드의
# team 필드로만 결정되므로 타 테넌트 사칭이 가능하다. WEBHOOK_SECRET_MAP 은
# `teamId=secret` 쌍 목록으로 "그 시크릿이 대변할 수 있는 팀 집합" 을 못 박아,
# 서명에 성공한 시크릿과 페이로드가 주장하는 팀의 일치를 강제한다.
#   형식: `uuid-a=sec1,uuid-b=sec2` (같은 팀 키 반복 = 로테이션, 같은 시크릿 반복 = 다팀 허용)
#   저장: secret → {teamId, ...} (검증이 "일치한 시크릿" 기준으로 이뤄지므로 역방향 색인)
WEBHOOK_SECRET_TEAMS: dict[str, set] = {}
WEBHOOK_SECRET_MAP_CONFIGURED = False

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


def verify_signature_match(payload: bytes, signature: str, secrets: list):
    """서명이 맞는 첫 후보 시크릿을 반환(없으면 None).

    "통과했다" 만으로는 크로스테넌트 바인딩을 걸 수 없다 — 어느 시크릿이 맞았는지
    알아야 그 시크릿에 바인딩된 팀 집합과 페이로드가 주장하는 팀을 대조할 수 있다.
    """
    for s in secrets:
        if verify_signature(payload, signature, s):
            return s
    return None


def verify_signature_any(payload: bytes, signature: str, secrets: list) -> bool:
    """후보 시크릿 중 하나라도 서명이 맞으면 통과 (프로젝트별 워크스페이스 대응)."""
    return verify_signature_match(payload, signature, secrets) is not None


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
            "received_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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


def _extract_team_id(data: dict):
    """Linear 페이로드에서 팀 식별자를 뽑는다 — data.teamId(현행) → data.team.id(방어).

    귀속(LLM 인제스트)과 크로스테넌트 바인딩 검증이 같은 값을 봐야 하므로 한 곳에 둔다.
    두 경로가 갈리면 "검증한 팀" 과 "귀속된 팀" 이 달라져 바인딩이 우회된다.
    """
    if not isinstance(data, dict):
        return None
    team_id = data.get("teamId")
    if not team_id:
        team = data.get("team")
        team_id = team.get("id") if isinstance(team, dict) else None
    # 문자열만 팀 식별자로 인정 — dict/list 가 오면 바인딩 대조(:in)에서 unhashable
    # 예외로 커넥션이 끊긴다(적대적 재검 발견 1). None 반환이면 fail-closed 403.
    return team_id if isinstance(team_id, str) and team_id else None


def _payload_team_id(payload: dict):
    """webhook 페이로드 전체에서 팀 식별자를 찾는다(data 우선, 최상위 폴백)."""
    team_id = _extract_team_id(payload.get("data") if isinstance(payload, dict) else None)
    if team_id:
        return team_id
    return _extract_team_id(payload)


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
        team_id = _extract_team_id(data)
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

        # 서명 검증. CONFIGURED 는 참인데 목록이 비었으면(공백만 설정 등) 검증을 끄지 않고
        # 전부 거부한다 — main() 이 기동을 거부하므로 통상 도달하지 않는 2차 방어선.
        matched_secret = None
        if WEBHOOK_SECRETS or WEBHOOK_SECRETS_CONFIGURED or WEBHOOK_SECRET_MAP_CONFIGURED:
            signature = self.headers.get("Linear-Signature", "")
            matched_secret = verify_signature_match(body, signature, WEBHOOK_SECRETS)
            if matched_secret is None:
                log("REJECTED: 서명 검증 실패")
                self._respond(401, {"error": "invalid signature"})
                return

        # JSON 파싱
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self._respond(400, {"error": "invalid json"})
            return

        # 크로스테넌트 바인딩 검증 — 일치한 시크릿이 MAP 출신일 때만 적용한다.
        # 이벤트 종류를 가리지 않는다(type/action 필터는 그 뒤 _handle_event 의 몫):
        # 사칭은 Issue 이벤트에만 오는 것이 아니므로 서명 통과 지점에서 한 번에 막는다.
        # 비바인딩 시크릿(WEBHOOK_SECRET/WEBHOOK_SECRETS 출신, 레거시 단일 테넌트)은
        # 검사 없이 통과 — 기존 배포 회귀 0.
        if matched_secret is not None and matched_secret in WEBHOOK_SECRET_TEAMS:
            bound_teams = WEBHOOK_SECRET_TEAMS[matched_secret]
            claimed_team = _payload_team_id(payload)
            if not claimed_team:
                # fail-closed: 팀을 확인할 수 없으면 바인딩을 강제할 수 없다.
                log("REJECTED: 바인딩 시크릿 요청에 팀 식별자 없음 (fail-closed)")
                self._respond(403, {"error": "team binding required"})
                return
            if claimed_team not in bound_teams:
                log(f"REJECTED: 크로스테넌트 — 서명 시크릿에 바인딩되지 않은 팀 {claimed_team}")
                self._respond(403, {"error": "team mismatch"})
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


def _split_secrets(raw: str) -> list:
    """콤마 구분 시크릿 문자열 → 공백 트림·빈 항목 제거된 목록."""
    return [s.strip() for s in raw.split(",") if s.strip()]


def _parse_secret_map(raw: str) -> dict:
    """`teamId=secret` 콤마 목록 → {secret: {teamId, ...}} 역방향 색인.

    검증은 "일치한 시크릿" 을 기점으로 하므로 시크릿을 키로 둔다. 같은 teamId 가 여러 번
    나오면(로테이션) 각 시크릿이 그 팀을 대변하고, 같은 시크릿이 여러 팀에 나오면 그
    시크릿의 팀 집합이 넓어진다. 무효 항목은 조용히 버리지 않고 경고를 남긴다 —
    오타 한 줄이 해당 프로젝트를 무성이 거부 상태로 만들기 때문. (시크릿 값은 로그 금지)
    """
    mapping: dict[str, set] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            log("WARN: WEBHOOK_SECRET_MAP 항목에 '=' 가 없어 무시 (형식: teamId=secret)")
            continue
        team, secret = item.split("=", 1)
        team, secret = team.strip(), secret.strip()
        if not team or not secret:
            log(f"WARN: WEBHOOK_SECRET_MAP 무효 항목 무시 (team={team or '<빈값>'})")
            continue
        mapping.setdefault(secret, set()).add(team)
    return mapping


def load_env():
    """Load webhook secrets from env vars or .env.

    WEBHOOK_SECRET(단일, 기존 계약)과 WEBHOOK_SECRETS(콤마 구분, 프로젝트별)를 모두 읽어
    WEBHOOK_SECRETS 목록으로 합친다. 단일 시크릿만 설정된 환경은 목록 길이 1 → 동작 동일.

    trim 전 원문(raw)을 따로 보관해 WEBHOOK_SECRETS_CONFIGURED 를 판정한다 — 공백만
    설정된 값이 파싱 후 빈 목록이 되어 검증이 통째로 꺼지는 fail-open 을 막기 위함.
    """
    global WEBHOOK_SECRET, WEBHOOK_SECRETS, WEBHOOK_SECRETS_CONFIGURED
    global WEBHOOK_SECRET_TEAMS, WEBHOOK_SECRET_MAP_CONFIGURED

    raw_single = os.getenv("WEBHOOK_SECRET", "")
    raw_multi = os.getenv("WEBHOOK_SECRETS", "")
    raw_map = os.getenv("WEBHOOK_SECRET_MAP", "")

    # env 로 아무것도 안 온 항목만 .env 폴백으로 채운다(env 우선, 기존 우선순위 유지).
    if not raw_single or not raw_multi or not raw_map:
        env_path = os.path.join(PROJECT_DIR, ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not raw_single and line.startswith("WEBHOOK_SECRET="):
                        raw_single = raw_line.split("=", 1)[1].rstrip("\r\n")
                    elif not raw_multi and line.startswith("WEBHOOK_SECRETS="):
                        raw_multi = raw_line.split("=", 1)[1].rstrip("\r\n")
                    elif not raw_map and line.startswith("WEBHOOK_SECRET_MAP="):
                        raw_map = raw_line.split("=", 1)[1].rstrip("\r\n")

    WEBHOOK_SECRETS_CONFIGURED = bool(raw_single or raw_multi)
    WEBHOOK_SECRET_MAP_CONFIGURED = bool(raw_map)
    single = raw_single.strip()
    multi = raw_multi.strip()

    WEBHOOK_SECRET = single or None
    WEBHOOK_SECRET_TEAMS = _parse_secret_map(raw_map)

    # 바인딩 시크릿도 서명 후보에 합류해야 검증을 통과한다. 목록에 이미 있는 시크릿이
    # MAP 에도 있으면 바인딩이 이긴다(WEBHOOK_SECRET_TEAMS 조회가 우선) — 같은 값을
    # 비바인딩으로도 등록해 팀 검사를 우회하는 것을 막는다.
    merged = []
    for candidate in (
        ([single] if single else []) + _split_secrets(multi) + list(WEBHOOK_SECRET_TEAMS)
    ):
        if candidate not in merged:
            merged.append(candidate)
    WEBHOOK_SECRETS = merged


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
    #   세 소스(WEBHOOK_SECRET / WEBHOOK_SECRETS / WEBHOOK_SECRET_MAP) 를 통틀어 유효
    #   시크릿이 0개면 거부한다(WEBHOOK_SECRETS 에 MAP 출신도 합류해 있다).
    if ENQUEUE_ONLY and not WEBHOOK_SECRETS:
        log(
            "FATAL: 수신전용 모드는 시크릿 필수(공개 노출부) — "
            "WEBHOOK_SECRET(S)/WEBHOOK_SECRET_MAP 미설정, 기동 거부"
        )
        sys.exit(2)

    # fail-closed: 시크릿을 설정하려는 의도가 명백한데(환경변수에 값 존재) 파싱 결과가
    #   0개면 오타/공백 설정이다. 검증을 조용히 끄면 호스트 단독 모드가 무방비가 되므로
    #   기동을 거부한다. 완전 미설정(두 변수 모두 없음)은 기존 경고 동작 그대로 — 회귀 0.
    if (WEBHOOK_SECRETS_CONFIGURED or WEBHOOK_SECRET_MAP_CONFIGURED) and not WEBHOOK_SECRETS:
        log(
            "FATAL: WEBHOOK_SECRET(S)/WEBHOOK_SECRET_MAP 이 설정됐으나 유효한 시크릿이 "
            "0개(공백/빈 항목/형식 오류) — 기동 거부"
        )
        sys.exit(2)

    # MAP 만 형식 오류인 경우도 조용히 넘기지 않는다 — 다른 소스 덕에 시크릿 수는 채워지지만
    # 해당 프로젝트는 바인딩 없이 거부되므로, 설정 의도와 실제가 어긋난 상태로 뜨게 된다.
    if WEBHOOK_SECRET_MAP_CONFIGURED and not WEBHOOK_SECRET_TEAMS:
        log("FATAL: WEBHOOK_SECRET_MAP 이 설정됐으나 유효한 teamId=secret 항목이 0개 — 기동 거부")
        sys.exit(2)

    server = HTTPServer(("0.0.0.0", args.port), WebhookHandler)
    log(f"Linear Webhook 서버 시작: http://0.0.0.0:{args.port}")
    log(f"  Webhook URL: http://<서버IP>:{args.port}/webhook/linear")
    log(f"  Health check: http://localhost:{args.port}/health")
    log(
        f"  서명 검증: {f'활성 (시크릿 {len(WEBHOOK_SECRETS)}개)' if WEBHOOK_SECRETS else '비활성 (WEBHOOK_SECRET 미설정)'}"
    )
    bound_teams = {t for teams in WEBHOOK_SECRET_TEAMS.values() for t in teams}
    log(
        f"  팀 바인딩: 시크릿 {len(WEBHOOK_SECRET_TEAMS)}개 / 팀 {len(bound_teams)}개"
        if WEBHOOK_SECRET_TEAMS
        else "  팀 바인딩: 없음 (WEBHOOK_SECRET_MAP 미설정 — 레거시 단일 테넌트)"
    )
    # 바인딩과 비바인딩(레거시) 시크릿이 공존하면 레거시 시크릿은 팀 검사 없이 통과한다
    # (적대적 재검 발견 2). 크로스테넌트 차단을 완성하려면 레거시 변수를 비워야 한다.
    unbound = [s for s in WEBHOOK_SECRETS if s not in WEBHOOK_SECRET_TEAMS]
    if WEBHOOK_SECRET_TEAMS and unbound:
        log(
            f"  WARN: 비바인딩 시크릿 {len(unbound)}개 공존 — 해당 시크릿 서명은 팀 검사를 "
            "받지 않는다. 멀티 테넌트 운영이면 WEBHOOK_SECRET(S) 를 비우고 MAP 만 쓸 것."
        )
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
