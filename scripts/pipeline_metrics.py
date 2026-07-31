#!/usr/bin/env python3
"""파이프라인 메트릭 수집기 (파생형 하네스 Tier 3a) — 실행 이벤트 JSONL 원장 append.

티켓 1건 처리마다 단계 경계에서 이벤트를 JSONL 로 누적한다. 이 원장이 이후
prompt-evolve 루프(3b, 별도 범위)의 채점 입력이 된다. **수집만** 한다 —
집계·판단·대시보드 없음.

한 줄 스키마(version 필드로 후방 호환):
  {"version": 1, "ts": "<ISO8601 UTC>", "run_id": "...", "event": "...", "data": {...}}

비차단 원칙: 어떤 실패(권한·디스크·불량 JSON 등)에도 exit 0(stderr 경고만).
관측이 파이프라인을 죽이면 안 된다. 단, argparse 사용법 오류만 기본 exit 2 허용.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

SCHEMA_VERSION = 1
DEFAULT_LEDGER = "logs/metrics/pipeline_runs.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_data(raw: str) -> dict:
    """--data 를 dict 로 파싱. 불량 JSON 이면 원문 보존({"raw": ...}) — 유실 금지."""
    if raw is None or raw == "":
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print(f"[pipeline_metrics] 경고: --data 불량 JSON — 원문 보존: {raw!r}",
              file=sys.stderr)
        return {"raw": raw}
    # 최상위가 객체가 아니면(리스트/스칼라) 원장 스키마 일관성을 위해 감싼다
    if not isinstance(parsed, dict):
        return {"raw": parsed}
    return parsed


def record(run_id: str, event: str, data: dict, ledger: str) -> None:
    """이벤트 1줄을 원장에 append. 실패는 삼키고 stderr 경고만(비차단)."""
    entry = {
        "version": SCHEMA_VERSION,
        "ts": _utc_now_iso(),
        "run_id": run_id,
        "event": event,
        "data": data,
    }
    line = json.dumps(entry, ensure_ascii=False)

    parent = os.path.dirname(ledger)
    if parent:
        try:
            os.makedirs(parent, exist_ok=True)
        except OSError as e:
            print(f"[pipeline_metrics] 경고: 로그 디렉터리 생성 실패({parent}): {e}",
                  file=sys.stderr)
            return
    try:
        with open(ledger, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as e:
        print(f"[pipeline_metrics] 경고: 원장 기록 실패({ledger}): {e}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="파이프라인 메트릭 수집기 (Harness Tier 3a)")
    p.add_argument("--run-id", required=True, help="실행 ID(예: <ISSUE_KEY>_<ts>)")
    p.add_argument("--event", required=True, help="이벤트 이름")
    p.add_argument("--data", default="", help="이벤트 데이터(JSON 문자열)")
    p.add_argument("--ledger", default=DEFAULT_LEDGER, help="JSONL 원장 경로")
    args = p.parse_args(argv)

    # 여기서부터는 어떤 예외도 exit 0 유지(파이프라인 비차단)
    try:
        data = _parse_data(args.data)
        record(args.run_id, args.event, data, args.ledger)
    except Exception as e:  # noqa: BLE001 - 최후 방어(관측이 파이프라인을 죽이지 않도록)
        print(f"[pipeline_metrics] 경고: 예기치 못한 오류(무시): {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
