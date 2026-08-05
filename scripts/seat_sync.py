#!/usr/bin/env python3
# seat_sync.py — DB 구독 시트(user_anthropic_credentials) → 로컬 원장(.ralph/seats.json) 동기화 (CE-400).
#
# 근본 문제: 로컬 seat_id 가 UUID 가 아니면 usage_ingest.py 의 _uuid_or_none 이 조용히
# 버려 llm_usage_ledger.seat_id 가 NULL 이 된다. 해결: DB 시트의 seat_id 값(전체 UUID
# 문자열, user_anthropic_credentials.id) 그대로를 로컬 원장에 등록한다.
#
# 순수 가산/갱신 — 어떤 실패(베이스 URL 미설정/네트워크/비-2xx)도 stderr 경고 후
# exit 1 로 알리되(호출부는 `|| true` 로 비차단 처리), 기존 원장 파일은 절대 건드리지 않는다.
# seat_map.py 의 순수 함수(load_ledger/register_seat/set_status/stamp/write_ledger)만
# 재사용하고 원장 로직을 재구현하지 않는다.
#
# stdlib 전용(requests 금지 — urllib.request 사용). 토큰 값은 절대 로그/출력하지 않는다.
#
# env:
#   FLOWOPS_GOVERNANCE_SERVICE_URL (→ API_URL 폴백)  — 베이스 URL
#   GOVERNANCE_SERVICE_TOKEN                         — X-Governance-Token 헤더(있을 때)
#
# 사용:
#   python3 scripts/seat_sync.py [--output .ralph/seats.json]

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seat_map as sm  # noqa: E402

PROVISION_PATH = "/api/v1/ops/seats/provision"
DEFAULT_TIMEOUT = 10.0
DEFAULT_OUTPUT = sm.DEFAULT_OUTPUT
STATUS_ACTIVE = "active"


def _warn(msg: str) -> None:
    """비차단 경고 — 토큰 값은 절대 포함하지 않는다."""
    sys.stderr.write("[seat-sync] " + msg + "\n")


def _base_url() -> str | None:
    base = os.environ.get("FLOWOPS_GOVERNANCE_SERVICE_URL") or os.environ.get("API_URL")
    return base.rstrip("/") if base else None


def fetch_provision(base_url: str, *, token: str | None, timeout: float) -> dict:
    """provision 엔드포인트 GET. 실패 시 예외를 그대로 전파(호출자가 처리)."""
    url = base_url + PROVISION_PATH
    req = Request(url, method="GET")
    if token:
        req.add_header("X-Governance-Token", token)
    with urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def _write_token_file(repo_root: str, seat_id: str, token: str) -> str | None:
    """토큰을 `.ralph/seats/<seat_id 전체>.token` 에 원자적으로 기록하고, 원장에 적을
    레포 루트 상대경로를 반환한다. 실패 시 None(해당 시트만 스킵, 경고).

    파일명은 seat_id 앞 8자가 아니라 전체 UUID 를 쓴다 — 8자 접두사만 쓰면 서로 다른
    시트의 UUID 앞 8자가 우연히 같을 때(생일 문제) 나중 시트가 먼저 시트의 토큰
    파일을 덮어써 원장 항목이 다른 사용자의 토큰을 참조하는 교차 오귀속이 생긴다.
    """
    rel_dir = os.path.join(".ralph", "seats")
    abs_dir = os.path.join(repo_root, rel_dir)
    rel_path = os.path.join(rel_dir, f"{seat_id}.token")
    abs_path = os.path.join(repo_root, rel_path)
    tmp_path = abs_path + ".tmp"
    try:
        os.makedirs(abs_dir, exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as fh:
            fh.write(token)
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, abs_path)
    except OSError as e:
        _warn(f"토큰 파일 기록 실패(시트 {seat_id} 스킵): {e}")
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return None
    return rel_path.replace(os.sep, "/")


def sync_seats(items: list[dict], ledger: dict, repo_root: str) -> dict:
    """provision 응답 항목들을 원장에 반영한다(순수화 어려운 IO 포함 — 파일 쓰기 수반).

    active → 토큰 파일 기록 + register_seat(status=active).
    비-active → 로컬에 이미 등재된 시트만 disabled 로 전환. 미등재 시 스킵(생성 안 함).
    응답에 없는 seat_id 는 여기서 아예 다뤄지지 않으므로 자동으로 보존된다.
    """
    new_ledger = ledger
    existing_seats: dict = dict(ledger.get("seats") or {})
    for item in items:
        seat_id = str(item.get("seat_id") or "")
        if not seat_id:
            continue
        status = item.get("seat_status")
        email = item.get("email") or ""
        token = item.get("token") or ""

        if status == STATUS_ACTIVE:
            token_file = _write_token_file(repo_root, seat_id, token)
            if token_file is None:
                continue
            try:
                new_ledger = sm.register_seat(
                    new_ledger,
                    seat_id,
                    token_file=token_file,
                    label=email,
                    status=STATUS_ACTIVE,
                )
            except ValueError as e:
                _warn(f"시트 등재 실패(스킵): {e}")
                continue
        else:
            if seat_id in existing_seats:
                try:
                    new_ledger = sm.set_status(new_ledger, seat_id, "disabled")
                except (KeyError, ValueError) as e:
                    _warn(f"시트 상태 변경 실패(스킵): {e}")
                    continue
            # 로컬에 없는 비-active 시트는 생성하지 않는다(스킵).
    return new_ledger


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DB 구독 시트 → 로컬 원장 동기화 (CE-400)")
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT, help=f"원장 경로 (기본: {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args(argv)

    base = _base_url()
    if not base:
        _warn("베이스 URL 미설정(FLOWOPS_GOVERNANCE_SERVICE_URL/API_URL) — 동기화 스킵")
        return 1

    token = os.environ.get("GOVERNANCE_SERVICE_TOKEN") or None
    try:
        data = fetch_provision(base, token=token, timeout=DEFAULT_TIMEOUT)
    except HTTPError as e:
        _warn(f"조회 HTTP 오류: {e.code} {getattr(e, 'reason', '')}")
        return 1
    except (URLError, OSError, ValueError, json.JSONDecodeError) as e:
        _warn(f"조회 실패: {e}")
        return 1

    items = data.get("seats") if isinstance(data, dict) else None
    if not isinstance(items, list):
        _warn("응답 형식 이상(seats 목록 없음) — 동기화 스킵")
        return 1

    output = args.output
    repo_root = sm.base_dir_for(output)
    existing = sm.load_ledger(output)
    ledger = existing if existing is not None else sm.empty_ledger()

    new_ledger = sync_seats(items, ledger, repo_root)
    sm.write_ledger(output, sm.stamp(existing, new_ledger))
    _warn(f"동기화 완료: {len(items)}건 처리")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        return run(argv)
    except SystemExit as e:
        _warn(f"인자 오류: {e}")
        return 1
    except Exception as e:  # noqa: BLE001 — 파이프라인 보호가 최우선(호출부 || true)
        _warn(f"예기치 못한 오류: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
