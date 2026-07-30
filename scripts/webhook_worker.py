#!/usr/bin/env python3
"""ClickEye 웹훅 실행 워커 (호스트 전용).

수신전용 웹훅(컨테이너, WEBHOOK_ENQUEUE_ONLY=true)이 Redis 큐에 적재한 job 을
호스트에서 BLPOP 으로 꺼내 실제 실행(auto_dev_pipeline.sh / linear_confirmer.py)한다.

── 왜 실행이 호스트에 있는가 ─────────────────────────────────────────────────
파이프라인(auto_dev_pipeline.sh)은 git(29회) + claude CLI + uv/npm 게이트를 쓴다.
컨테이너에서는 호스트 프로세스·구독 세션·git 크리덴셜을 그대로 쓸 수 없으므로,
네트워크 노출부(수신)만 컨테이너화하고 실행은 호스트 워커에 남긴다. 토큰·git
크리덴셜을 컨테이너에 복사하지 않는 것이 이 분리 설계의 핵심 이점이다.

── 큐 계약 (두 트랙 공유 — 이 정의를 벗어나지 말 것) ─────────────────────────
  키:      clickeye:webhook:jobs (Redis LIST)
  적재:    RPUSH (webhook_server._enqueue_job)
  소비:    BLPOP (이 워커) — FIFO
  페이로드: {"kind": "pipeline"|"confirmer",
            "identifier": "CE-123",
            "state": "DayQueued",
            "received_at": "<ISO8601 UTC>"}
  REDIS_URL 기본 redis://localhost:6379/0

── 사용법 ────────────────────────────────────────────────────────────────────
  python3 scripts/webhook_worker.py            # 상시 루프(BLPOP 무한 대기)
  python3 scripts/webhook_worker.py --once     # 1건 처리 후 종료(cron 용).
                                               # 큐가 비어 있으면 exit 0(에러 아님)
  python3 scripts/webhook_worker.py --once --dry-run
                                               # 배관 스모크: trigger_* 를 실행하지
                                               # 않고(webhook_server.DRY_RUN=True) 큐→
                                               # 디스패치 경로만 검증

── 순차 처리 ─────────────────────────────────────────────────────────────────
job 은 한 번에 하나씩 순차 디스패치한다(동시 실행 금지).
- pipeline: trigger_pipeline 이 반환한 Popen 을 .wait() 로 대기(결정적 신호)한 뒤,
  _reap 이 유발할 수 있는 재트리거 체인까지 idle 이 될 때까지 추가 대기한다.
- confirmer: trigger_confirmer 가 반환한 Popen 을 .wait() 로 대기해 파이프라인과
  겹치지 않게 한다.
프로세스 간(별도 --once cron 다중 기동) 동시성은 파이프라인 내부의
.ralph/.pipeline_lock 파일락이 최종 보장한다(정합).

── 큐 신뢰성 (at-most-once — 신뢰 큐 아님) ───────────────────────────────────
이 워커는 at-most-once 로 동작한다:
  · BLPOP 으로 꺼낸 직후 dispatch 전에 워커가 크래시하면 그 job 은 유실된다.
  · 잘못된 JSON·미지원 kind 는 폐기한다(로그만 남김).
유실 복구는 폴링 cron 이 담당하며 비대칭이다(clickeye_cron.txt):
  · pipeline: 평일 09~18시 */5 폴링(auto_dev_pipeline.sh --once)이 잔여 Queued 재스캔.
  · confirmer: 평일 정오 1회 cron(linear_confirmer.py)만 → 최대 ~24h(주말 포함 더) 지연.
신뢰성이 필요하면 후속 티켓에서 BRPOPLPUSH(처리중 리스트) + 완료 시 LREM 패턴으로
전환한다(run_guide 트러블슈팅에 처리중 리스트 확인 절차 병기).

로직은 webhook_server 의 trigger_pipeline·trigger_confirmer·log 를 재사용한다(복제
금지). webhook_server 는 `if __name__ == "__main__"` 가드가 있어 import 만으로 HTTP
서버가 기동되지 않는다.
"""

import argparse
import json
import os
import subprocess
import sys
import time

try:
    import redis
except ImportError:
    redis = None

sys.path.insert(0, os.path.dirname(__file__))

# webhook_server 는 __main__ 가드가 있어 import 시 서버가 기동되지 않는다(확인함).
# trigger_*·log 를 재사용(로직 복제 금지). _pipeline_lock 은 파이프라인 수명과
# 동기화된 메모리 락으로, 재트리거 체인 idle 판정에 재사용한다. 모듈 참조(ws)는
# --dry-run 에서 DRY_RUN 플래그를 세팅하는 용도.
import webhook_server as ws  # noqa: E402
from webhook_server import (  # noqa: E402
    trigger_pipeline,
    trigger_confirmer,
    _pipeline_lock,
    log,
    QUEUE_KEY,
    REDIS_URL,
)

BLPOP_TIMEOUT = 5      # 초 — --once 가 빈 큐에서 빠르게 빠져나오도록 짧게
IDLE_POLL = 3.0        # 초 — 파이프라인 idle 판정 폴링 간격
IDLE_CONSEC = 3        # 회 — 연속 미락(unlocked) 판정(≈9s > 재트리거 5s 창)
RECONNECT_MAX = 30.0   # 초 — 재접속 백오프 상한

# _process_one 반환 신호(bool True 와 구분되는 예약 객체).
_EMPTY = object()       # 큐 비어 있음(timeout)
_CONN_ERROR = object()  # Redis 연결 오류(재접속 필요)


def _get_redis(exit_on_fail: bool = True):
    """redis 클라이언트 확보. 미설치/미접속은 명확한 에러로 안내(조용한 실패 금지).

    exit_on_fail=True(기본): 실패 시 non-zero exit. False(재접속 경로): None 반환."""
    if redis is None:
        log("ERROR: redis 파이썬 패키지 미설치. `pip install redis` 후 재실행하세요.")
        if exit_on_fail:
            sys.exit(3)
        return None
    try:
        client = redis.from_url(REDIS_URL)
        client.ping()
        return client
    except Exception as e:
        log(f"ERROR: Redis 접속 실패({REDIS_URL}) — {e}. redis 서버 기동 여부를 확인하세요.")
        if exit_on_fail:
            sys.exit(4)
        return None


def _wait_pipeline_idle(max_wait: float = 600.0):
    """실행 중인 파이프라인 체인이 모두 끝날(idle) 때까지 대기(순차 보장).

    _reap 은 파이프라인 종료 후 _pipeline_lock 을 release 하고 _check_and_retrigger 로
    잔여 큐를 재트리거한다. 그 재트리거는 acquire 전 5초 sleep 하므로 그 창에서 락이
    잠깐 풀린다 — 단발 폴링은 이를 idle 로 오판한다(리뷰 지적). 따라서 연속
    IDLE_CONSEC 회(≈IDLE_POLL×IDLE_CONSEC 초 > 5초) 모두 미락일 때만 idle 로 본다.
    """
    consec = 0
    waited = 0.0
    while waited < max_wait:
        if _pipeline_lock.locked():
            consec = 0
        else:
            consec += 1
            if consec >= IDLE_CONSEC:
                return
        time.sleep(IDLE_POLL)
        waited += IDLE_POLL


def _dispatch_pipeline(client, job: dict):
    """pipeline job: 트리거 후 프로세스 완료까지 대기(순차). 미점화는 idle 대기 후 재시도·재적재."""
    identifier = job.get("identifier", "?")
    res = trigger_pipeline()
    if isinstance(res, subprocess.Popen):
        res.wait()             # 이 파이프라인 프로세스 종료까지 대기(결정적 신호)
        _wait_pipeline_idle()  # _reap 재트리거 체인까지 idle 대기(순차 보장)
        return
    if res is True:            # DRY_RUN — 실행 안 함
        return
    # res is False → 미점화(이미 실행 중 or 최소간격 미도달). idle 대기 후 1회 재시도.
    log(f"WARN: {identifier} 파이프라인 미점화 — idle 대기 후 1회 재시도")
    _wait_pipeline_idle()
    res = trigger_pipeline()
    if isinstance(res, subprocess.Popen):
        res.wait()
        _wait_pipeline_idle()
        return
    if res is True:
        return
    # 최종 실패 → job 재적재(유실 방지). 폴링 cron 이 복구.
    try:
        client.rpush(QUEUE_KEY, json.dumps(job))
        log(f"WARN: {identifier} 재점화 실패 — job 재적재(폴링 cron 복구 대기)")
    except Exception as e:
        log(f"WARN: {identifier} 재점화 실패 — job 재적재도 실패({e}). 폴링 cron 복구 대기")
    time.sleep(IDLE_POLL)  # 재적재 직후 즉시 재소비 hot-loop 방지


def dispatch(client, job: dict):
    """job.kind 에 따라 실행 함수로 디스패치. 순차 처리."""
    kind = job.get("kind")
    identifier = job.get("identifier", "?")
    state = job.get("state", "?")

    if kind == "pipeline":
        log(f"DISPATCH: pipeline {identifier} (state={state})")
        _dispatch_pipeline(client, job)
    elif kind == "confirmer":
        # confirmer 도 순차 보장: proc 핸들을 .wait() 로 대기(파이프라인과 겹침 방지).
        log(f"DISPATCH: confirmer {identifier} (state={state})")
        res = trigger_confirmer()
        if isinstance(res, subprocess.Popen):
            res.wait()
    else:
        log(f"SKIP: 미지원 kind={kind!r} (identifier={identifier}) — job 폐기")


def _process_one(client, block: bool):
    """큐에서 1건 처리. 처리=True / 빈 큐=_EMPTY / 연결오류=_CONN_ERROR.

    잘못된 JSON·미지원 kind 는 로그 후 소비(True) — 워커가 죽지 않도록."""
    # block=False(--once): timeout 후 None → 빈 큐. block=True(상시): 무한 대기(timeout 0).
    try:
        res = client.blpop(QUEUE_KEY, timeout=(BLPOP_TIMEOUT if not block else 0))
    except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
        # blpop 은 블로킹 명령이라 redis-py 기본 재시도에 의존할 수 없다 → 상위에서 재접속.
        log(f"WARN: Redis 연결 오류 — {e}")
        return _CONN_ERROR
    if res is None:
        return _EMPTY  # 큐 비어 있음(--once 정상 종료 경로)

    _key, raw = res
    try:
        payload = raw.decode() if isinstance(raw, (bytes, bytearray)) else raw
        job = json.loads(payload)
    except (ValueError, AttributeError) as e:
        log(f"WARN: 잘못된 job JSON 폐기 — {e}: {raw!r}")
        return True  # 1건 소비함(--once 는 여기서 종료)

    try:
        dispatch(client, job)
    except Exception as e:
        # 디스패치 중 예외로 워커가 죽지 않도록 방어(다음 job 으로 진행).
        log(f"ERROR: job 처리 실패(무시하고 계속) — {e}: {job!r}")
    return True


def main():
    parser = argparse.ArgumentParser(description="ClickEye 웹훅 실행 워커(호스트)")
    parser.add_argument(
        "--once", action="store_true",
        help="1건 처리 후 종료(cron 용). 큐가 비어 있으면 exit 0.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="trigger_* 를 실행하지 않고(webhook_server.DRY_RUN=True) 배관만 검증(스모크).",
    )
    args = parser.parse_args()

    if args.dry_run:
        ws.DRY_RUN = True  # trigger_* 가 실제 실행 대신 로그만 남기고 True 반환

    client = _get_redis()

    if args.once:
        res = _process_one(client, block=False)
        if res is _CONN_ERROR:
            sys.exit(4)  # 연결 오류 — 다음 cron 이 재시도
        if res is _EMPTY:
            log("IDLE: 큐 비어 있음 — 처리할 job 없음(정상 종료).")
        sys.exit(0)

    # 상시 루프: BLPOP 무한 대기로 순차 소비. 연결 오류는 백오프 재접속으로 살아남는다.
    log(f"웹훅 워커 시작(상시): {REDIS_URL} 큐={QUEUE_KEY}. Ctrl+C 종료.")
    backoff = 1.0
    try:
        while True:
            try:
                res = _process_one(client, block=True)
            except Exception as e:
                # 예상 외 예외에도 프로세스가 죽지 않도록(무인 체인 정지 방지).
                log(f"ERROR: 루프 예외(계속) — {e}")
                time.sleep(IDLE_POLL)
                continue
            if res is _CONN_ERROR:
                log(f"RECONNECT: {backoff:.0f}s 후 Redis 재접속 시도")
                time.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX)
                new_client = _get_redis(exit_on_fail=False)
                if new_client is not None:
                    client = new_client
                    backoff = 1.0
                continue
            backoff = 1.0  # 정상 처리/빈 큐 → 백오프 리셋
    except KeyboardInterrupt:
        log("워커 종료")


if __name__ == "__main__":
    main()
