#!/usr/bin/env python3
# seat_quota_ingest.py — 러너 `cswap --list --json` 계정 잔량 → 서버 원장 인제스트 (CE-387).
#
# 러너 서버(계정 스왑 CLI) 가 보고하는 계정별 5시간/7일/스코프 잔량(schemaVersion 1)을
# 그대로 서버 `POST /api/v1/ops/seat-quota/snapshots` 에 전달한다. `usage_ingest.py`
# (CE-328)와 동일한 비차단 계약: 어떤 실패(cswap 부재/파싱/네트워크/4xx 등)도 stderr
# 경고 한 줄 후 exit 0 으로 삼켜 절대 호출측(크론/파이프라인)을 죽이지 않는다.
#
# stdlib 전용(requests 금지 — urllib.request 사용). usage_ingest.py 와 헬퍼를 공유하지
# 않는 독립 파일이다(기존 스크립트도 동일 패턴).
#
# env:
#   FLOWOPS_GOVERNANCE_SERVICE_URL (→ API_URL 폴백) — 인제스트 베이스 URL
#   GOVERNANCE_SERVICE_TOKEN                        — X-Governance-Token 헤더(있을 때)
#   FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT              — 전송 타임아웃(초, 기본 10)
#   CSWAP_BIN                                       — cswap 실행 파일 경로(기본 "cswap")
#
# 사용:
#   python3 scripts/seat_quota_ingest.py
#
# 크론 예시(실제 등록은 하지 않음 — 5분 주기):
#   */5 * * * * cd /path/to/ClickEye && python3 scripts/seat_quota_ingest.py >> logs/seat_quota_ingest.log 2>&1

from __future__ import annotations

import json
import os
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

INGEST_PATH = "/api/v1/ops/seat-quota/snapshots"
DEFAULT_TIMEOUT = 10.0


def _warn(msg: str) -> None:
    """비차단 경고 — 조용한 손실 방지용 로그만 남긴다."""
    sys.stderr.write("[seat-quota-ingest] " + msg + "\n")


def run_cswap(cswap_bin: str | None = None) -> str | None:
    """`cswap --list --json` 을 실행해 stdout(JSON 문자열)을 반환.

    cswap 미설치(FileNotFoundError) → None(조용히 skip). 그 외 서브프로세스 오류도
    호출자가 삼키도록 None 을 반환하며 경고만 남긴다.
    """
    bin_path = cswap_bin or os.environ.get("CSWAP_BIN") or "cswap"
    try:
        proc = subprocess.run(
            [bin_path, "--list", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        _warn("cswap 미설치 — 인제스트 스킵")
        return None
    except (subprocess.TimeoutExpired, OSError) as e:
        _warn("cswap 실행 실패(비차단): %s" % e)
        return None

    if proc.returncode != 0:
        _warn("cswap 종료코드 %s(비차단): %s" % (proc.returncode, (proc.stderr or "").strip()[:200]))
        return None
    return proc.stdout


def build_payload(cswap_stdout: str) -> dict | None:
    """cswap stdout(JSON 문자열) → 배치 요청 payload({"accounts": [...]}).

    cswap 최상위 응답은 {"schemaVersion": 1, "accounts": [...]} 형태를 가정한다.
    파싱 실패/accounts 부재 시 None(호출자가 skip 처리).
    """
    try:
        data = json.loads(cswap_stdout)
    except (ValueError, json.JSONDecodeError) as e:
        _warn("cswap 출력 파싱 실패(비차단): %s" % e)
        return None

    if not isinstance(data, dict):
        _warn("cswap 출력이 JSON 오브젝트가 아님 — 인제스트 스킵")
        return None

    accounts = data.get("accounts")
    if not isinstance(accounts, list) or not accounts:
        _warn("accounts 없음/빈 배열 — 인제스트 스킵")
        return None

    return {"accounts": accounts}


def _base_url(api_url_arg: str | None = None) -> str | None:
    """베이스 URL 폴백: --api-url → FLOWOPS_GOVERNANCE_SERVICE_URL → API_URL."""
    base = (
        api_url_arg
        or os.environ.get("FLOWOPS_GOVERNANCE_SERVICE_URL")
        or os.environ.get("API_URL")
    )
    return base.rstrip("/") if base else None


def post_snapshots(payload: dict, base_url: str, *, token: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> str:
    """서버 인제스트 엔드포인트로 POST. 응답 본문(문자열)을 반환.

    네트워크/HTTP 오류는 호출자(main)가 삼키도록 예외를 그대로 전파한다.
    """
    url = base_url + INGEST_PATH
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Governance-Token", token)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _timeout() -> float:
    raw = os.environ.get("FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT")
    try:
        return float(raw) if raw else DEFAULT_TIMEOUT
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def run(argv: list[str] | None = None) -> int:  # noqa: ARG001 — argv 는 인터페이스 일관성 유지용
    stdout = run_cswap()
    if stdout is None:
        return 0

    payload = build_payload(stdout)
    if payload is None:
        return 0

    base = _base_url(os.environ.get("SEAT_QUOTA_API_URL"))
    if not base:
        _warn("베이스 URL 미설정(FLOWOPS_GOVERNANCE_SERVICE_URL/API_URL) — 인제스트 스킵")
        return 0

    token = os.environ.get("GOVERNANCE_SERVICE_TOKEN") or None
    try:
        body = post_snapshots(payload, base, token=token, timeout=_timeout())
        _warn("전송 완료: %s" % (body or "").strip()[:200])
    except HTTPError as e:
        _warn("전송 HTTP 오류(비차단) %s: %s" % (e.code, getattr(e, "reason", "")))
    except (URLError, OSError, ValueError) as e:
        _warn("전송 실패(비차단): %s" % e)
    return 0


def main(argv: list[str] | None = None) -> int:
    # 최후 방어선 — 예기치 못한 예외까지 삼켜 항상 exit 0.
    try:
        return run(argv)
    except SystemExit as e:
        _warn("인자 오류(비차단): %s" % e)
        return 0
    except Exception as e:  # noqa: BLE001 — 파이프라인 보호가 최우선
        _warn("예기치 못한 오류(비차단): %s" % e)
        return 0


if __name__ == "__main__":
    sys.exit(main())
