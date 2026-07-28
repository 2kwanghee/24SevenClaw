#!/usr/bin/env python3
"""완주 오케스트레이터 — 재시도 원장 (다프로젝트화 P1, D-13).

무인 파이프라인에서 실패는 종료 사유가 아니라 **재시도 상태**다. 이 원장은 이슈별 실패
횟수를 영속 기록하고(프로세스 재시작에도 생존 — 재개 가능성), 한도 소진 시에만 터미널
판정을 내린다. 터미널이 있으면 파이프라인은 "완료"가 아니라 "정지(HALT)"로 보고해야 한다.

설계 근거: docs/multiproject-delivery.md §6-1 — 실패 티켓이 Backlog 로 이동하면
webhook 재트리거(Queued 계열만 조회)에서 영구 이탈하고 루프가 완료로 종료하는 결함.

stdlib 전용(governance 커널과 동일 제약 — 시스템 python3 로 설치 없이 호출).

exit 계약:
  record-failure → 0 = 재시도 가능(호출자는 이슈를 원래 Queued 상태로 복귀시킨다)
                   3 = 한도 소진 · 터미널(호출자는 Backlog + 코멘트 + 정지 보고)
  clear / status / reset → 0 (인자 오류 등은 argparse 가 2)

사용:
  python3 scripts/retry_ledger.py record-failure --issue CE-123 --reason "빌드 실패" [--limit 3]
  python3 scripts/retry_ledger.py clear --issue CE-123
  python3 scripts/retry_ledger.py status [--json]
  python3 scripts/retry_ledger.py reset
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from datetime import UTC, datetime

DEFAULT_LIMIT = 3
# P2(YAML 제어면)에서 retry_limits 로 이관될 자리 — 키 이름을 고정해 이관 무마찰.
LIMIT_ENV = "FLOWOPS_COMPLETION_MAX_RETRIES"
EXIT_RETRY = 0
EXIT_TERMINAL = 3


def _ledger_path(project_dir: str) -> str:
    return os.path.join(project_dir, ".ralph", "retry_ledger.json")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def load(project_dir: str) -> dict:
    """원장 로드. 파손된 JSON 은 빈 원장으로 — 원장 파손이 파이프라인을 죽여선 안 된다.

    단 파손 사실은 stderr 로 알린다. 조용한 초기화 금지 — 재시도 이력 유실은 곧
    "한도 소진 판정 리셋"이므로 관측되지 않으면 무한 재시도로 이어질 수 있다.
    """
    path = _ledger_path(project_dir)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print("[retry-ledger] WARN: 원장 형식 불량(비 dict) → 빈 원장으로 재시작", file=sys.stderr)
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"[retry-ledger] WARN: 원장 파손 → 빈 원장으로 재시작 ({e})", file=sys.stderr)
        return {}


def save(project_dir: str, ledger: dict) -> None:
    """원자적 쓰기 — 부분 쓰기로 원장이 파손되지 않도록 tmp 파일 후 rename."""
    path = _ledger_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".retry_ledger.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def resolve_limit(cli_limit: int | None) -> int:
    """한도 해석: CLI 명시 > env > 기본 3. 파싱 불가/0 이하는 기본값(결정적)."""
    if cli_limit is not None and cli_limit > 0:
        return cli_limit
    raw = os.environ.get(LIMIT_ENV, "").strip()
    if raw:
        try:
            v = int(raw)
            if v > 0:
                return v
        except ValueError:
            pass
    return DEFAULT_LIMIT


def record_failure(project_dir: str, issue: str, reason: str, limit: int) -> int:
    ledger = load(project_dir)
    entry = ledger.get(issue)
    if not isinstance(entry, dict):
        entry = {"attempts": 0, "first_failed_at": _now(), "terminal": False}
    entry["attempts"] = int(entry.get("attempts", 0)) + 1
    entry["last_reason"] = reason
    entry["last_failed_at"] = _now()
    entry["terminal"] = entry["attempts"] >= limit
    ledger[issue] = entry
    save(project_dir, ledger)

    if entry["terminal"]:
        print(
            f"[retry-ledger] TERMINAL: {issue} 실패 {entry['attempts']}/{limit} — "
            f"한도 소진. 정지(HALT) 보고 대상. 사유: {reason}"
        )
        return EXIT_TERMINAL
    print(f"[retry-ledger] RETRY: {issue} 실패 {entry['attempts']}/{limit} — Queued 복귀 대상")
    return EXIT_RETRY


def clear(project_dir: str, issue: str) -> int:
    ledger = load(project_dir)
    if issue in ledger:
        del ledger[issue]
        save(project_dir, ledger)
        print(f"[retry-ledger] CLEAR: {issue}")
    return 0


def status(project_dir: str, as_json: bool) -> int:
    ledger = load(project_dir)
    terminal = {k: v for k, v in ledger.items() if isinstance(v, dict) and v.get("terminal")}
    retrying = {k: v for k, v in ledger.items() if isinstance(v, dict) and not v.get("terminal")}
    if as_json:
        print(json.dumps({"terminal": terminal, "retrying": retrying}, ensure_ascii=False))
        return 0
    if terminal:
        print(f"🛑 터미널(정지 대상) {len(terminal)}건:")
        for k, v in terminal.items():
            print(f"  - {k}: {v.get('attempts', '?')}회 실패, 마지막 사유: {v.get('last_reason', '?')}")
    if retrying:
        print(f"🔄 재시도 중 {len(retrying)}건:")
        for k, v in retrying.items():
            print(f"  - {k}: {v.get('attempts', '?')}회 실패")
    if not ledger:
        print("원장 비어 있음 — 미결 실패 없음")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="완주 오케스트레이터 재시도 원장 (D-13)")
    p.add_argument("--project-dir", default=os.getcwd(), help="원장 기준 경로 (기본: cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    rf = sub.add_parser("record-failure", help="실패 1회 기록. exit 0=재시도 가능, 3=한도 소진")
    rf.add_argument("--issue", required=True)
    rf.add_argument("--reason", required=True)
    rf.add_argument("--limit", type=int, default=None, help=f"재시도 한도 (기본 {LIMIT_ENV} → {DEFAULT_LIMIT})")

    cl = sub.add_parser("clear", help="성공한 이슈의 실패 이력 제거")
    cl.add_argument("--issue", required=True)

    st = sub.add_parser("status", help="정지 보고용 요약")
    st.add_argument("--json", action="store_true")

    sub.add_parser("reset", help="원장 전체 초기화")

    a = p.parse_args()
    if a.cmd == "record-failure":
        return record_failure(a.project_dir, a.issue, a.reason, resolve_limit(a.limit))
    if a.cmd == "clear":
        return clear(a.project_dir, a.issue)
    if a.cmd == "status":
        return status(a.project_dir, a.json)
    if a.cmd == "reset":
        save(a.project_dir, {})
        print("[retry-ledger] RESET")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
