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
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCHEMA_VERSION = 1
DEFAULT_LEDGER = "logs/metrics/pipeline_runs.jsonl"

# 서버 원장 인제스트 (CE-363) — jsonl 기록 뒤에 서버로도 보낸다(비블로킹).
INGEST_PATH = "/api/v1/pipeline-runs/events"
DEFAULT_TIMEOUT = 10.0


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def record(run_id: str, event: str, data: dict, ledger: str, *, ts: str | None = None) -> None:
    """이벤트 1줄을 원장에 append. 실패는 삼키고 stderr 경고만(비차단).

    ts 를 주면 그 값을 쓴다(jsonl 과 서버 전송이 같은 시각을 공유하도록). 없으면 즉시 계산.
    """
    entry = {
        "version": SCHEMA_VERSION,
        "ts": ts or _utc_now_iso(),
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


def _base_url() -> str | None:
    """서버 원장 베이스 URL — 미설정이면 전송 생략(회귀 0)."""
    base = os.environ.get("FLOWOPS_GOVERNANCE_SERVICE_URL")
    return base.rstrip("/") if base else None


def _timeout() -> float:
    raw = os.environ.get("FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT")
    try:
        return float(raw) if raw else DEFAULT_TIMEOUT
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT


def post_event(
    run_id: str,
    event: str,
    data: dict,
    *,
    issue_key: str,
    project_id: str | None,
    workspace_key: str | None,
    ts: str,
) -> None:
    """이벤트 1건을 서버 원장(POST /pipeline-runs/events)으로 보낸다.

    **절대 실패하면 안 된다** — 네트워크·JSON·HTTP 오류를 전부 삼키고 stderr 경고 한 줄만
    남긴다(호출측 파이프라인 불사). URL 미설정 / issue_key 부재면 전송을 생략한다.
    """
    base = _base_url()
    if not base:
        return  # 서버 미설정 — 회귀 0
    if not issue_key:
        # issue_key 는 서버 필수 필드 — 없으면 상관 축을 만들 수 없어 전송 생략.
        print("[pipeline_metrics] 경고: issue_key 없음 — 서버 전송 생략", file=sys.stderr)
        return

    event_obj: dict = {
        "run_id": run_id,
        "issue_key": issue_key,
        "event": event,
        "data": data,
        "occurred_at": ts,
    }
    if project_id:
        event_obj["project_id"] = project_id
    if workspace_key:
        event_obj["workspace_key"] = workspace_key
    payload = json.dumps({"events": [event_obj]}).encode("utf-8")

    token = os.environ.get("GOVERNANCE_SERVICE_TOKEN")
    try:
        # Request 생성도 try 안에 둔다 — 스킴 없는 URL 은 여기서 ValueError 를 던진다(Py3.12).
        req = Request(base + INGEST_PATH, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-Governance-Token", token)
        with urlopen(req, timeout=_timeout()) as resp:  # noqa: S310 - 신뢰된 내부 URL
            resp.read()
    except HTTPError as e:
        print(f"[pipeline_metrics] 경고: 서버 전송 HTTP 오류(비차단) {e.code}", file=sys.stderr)
    except (URLError, OSError, ValueError) as e:
        print(f"[pipeline_metrics] 경고: 서버 전송 실패(비차단): {e}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="파이프라인 메트릭 수집기 (Harness Tier 3a)")
    p.add_argument("--run-id", required=True, help="실행 ID(예: <ISSUE_KEY>_<ts>)")
    p.add_argument("--event", required=True, help="이벤트 이름")
    p.add_argument("--data", default="", help="이벤트 데이터(JSON 문자열)")
    p.add_argument("--ledger", default=DEFAULT_LEDGER, help="JSONL 원장 경로")
    # 서버 원장 상관 축(CE-363) — 없으면 서버 전송 생략(jsonl 기록은 항상 유지).
    p.add_argument("--issue-key", default="", help="Linear 이슈 키(서버 필수 축)")
    p.add_argument("--project-id", default="", help="딜리버리 프로젝트 id(선택)")
    p.add_argument("--workspace-key", default="", help="워크스페이스 키(선택)")
    args = p.parse_args(argv)

    # 여기서부터는 어떤 예외도 exit 0 유지(파이프라인 비차단)
    try:
        data = _parse_data(args.data)
        ts = _utc_now_iso()
        record(args.run_id, args.event, data, args.ledger, ts=ts)
        post_event(
            args.run_id,
            args.event,
            data,
            issue_key=args.issue_key,
            project_id=args.project_id or None,
            workspace_key=args.workspace_key or None,
            ts=ts,
        )
    except Exception as e:  # noqa: BLE001 - 최후 방어(관측이 파이프라인을 죽이지 않도록)
        print(f"[pipeline_metrics] 경고: 예기치 못한 오류(무시): {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
