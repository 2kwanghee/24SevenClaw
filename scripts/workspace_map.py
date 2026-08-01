#!/usr/bin/env python3
"""workspace_map.py — 인테이크→워크스페이스 매핑 원장 갱신 (다프로젝트화 P5/F-4).

머신 조회 API(GET /api/v1/intake/machine/projects, X-ClickEye-Service-Key 인증)를
폴링해 `.ralph/workspaces.json` 매핑 원장을 **멱등** 갱신한다. 이 원장을
auto_dev_pipeline.sh 의 automap 이 읽어(이슈 제목 접두사 → workspace_key) 구현 대상
워크스페이스를 자동 선택한다.

원장 스키마:
  {
    "version": 1,
    "updated_at": "2026-08-01T00:00:00Z",
    "workspaces": {
      "[수주:3be49b62] ": {
        "workspace_key": "3be49b62",
        "intake_id": "3be49b62-....",
        "project_id": "....",
        "repo_source": "git@... 또는 로컬경로 | null",
        "status": "mapped" | "pending_source"
      }
    }
  }

설계 원칙:
- **추측 clone 금지**: repo_source 는 서버가 주지 않는다. 수동 기입(운영자)이 없으면
  `pending_source` 로 표기만 하고, 조달(workspace_provision.sh)은 소스가 채워진
  `mapped` 항목에 대해서만 별도로 수행한다.
- **수동 값 보존**: 기존 원장의 수동 기입 repo_source / workspace_key 는 폴링이
  덮어쓰지 않는다. 서버가 더는 반환하지 않는 기존 항목도 삭제하지 않는다(선등록 보존).
- **멱등**: 같은 입력 2회 = 동일 결과. workspaces 내용이 변하지 않으면 updated_at 도
  유지해 파일 내용이 바이트 단위로 동일하다.
- **비차단**: 이 스크립트 실패는 파이프라인을 막지 않는다 — automap 은 원장 파일을
  독립적으로 읽으며, 파일이 없거나 낡아도 self-repo 로 동작한다.

stdlib 만 사용(외부 의존 없음).

env: API_URL(기본 http://localhost:8000, intake 배치 스크립트 공통 컨벤션) ·
     CLICKEYE_SERVICE_KEY(X-ClickEye-Service-Key 평문)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

DEFAULT_OUTPUT = ".ralph/workspaces.json"
LEDGER_VERSION = 1
MACHINE_PROJECTS_PATH = "/api/v1/intake/machine/projects"


def _iso_now() -> str:
    """ISO8601 Z(초 단위) — 원장 updated_at 포맷."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_ledger(path: str) -> dict[str, Any] | None:
    """기존 원장을 읽는다. 없거나 파손 시 None(신규 생성 경로)."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        return None
    return None


def build_ledger(
    projects: list[dict[str, Any]],
    existing: dict[str, Any] | None,
    now: str | None = None,
) -> dict[str, Any]:
    """서버 프로젝트 목록 + 기존 원장 → 새 원장(순수 함수, HTTP·파일 I/O 없음).

    - 기존 항목의 repo_source / workspace_key(수동 값)는 보존한다.
    - repo_source 가 있으면 status=mapped, 없으면 pending_source.
    - 서버가 더는 반환하지 않는 기존 항목은 그대로 유지(선등록·수동 항목 보존).
    - workspaces 내용이 기존과 동일하면 updated_at 을 유지(멱등).
    """
    existing = existing or {}
    old_ws: dict[str, Any] = dict(existing.get("workspaces") or {})
    new_ws: dict[str, Any] = dict(old_ws)  # 기존 항목 보존에서 출발

    for proj in projects:
        prefix = proj.get("ticket_prefix")
        intake_id = proj.get("intake_id")
        if not prefix or not intake_id:
            continue  # 필수 값 없는 항목은 건너뛴다(서버 계약 위반 방어)
        prev = old_ws.get(prefix) or {}
        # 수동 값 보존: 기존 repo_source / workspace_key 우선.
        repo_source = prev.get("repo_source")
        workspace_key = prev.get("workspace_key") or str(intake_id)[:8]
        status = "mapped" if repo_source else "pending_source"
        new_ws[prefix] = {
            "workspace_key": workspace_key,
            "intake_id": str(intake_id),
            "project_id": str(proj.get("project_id")) if proj.get("project_id") else None,
            "repo_source": repo_source,
            "status": status,
        }

    # 멱등: workspaces 가 변하지 않았으면 updated_at 유지 → 파일 내용 동일.
    if new_ws == old_ws and existing.get("version") == LEDGER_VERSION:
        updated_at = existing.get("updated_at") or (now or _iso_now())
    else:
        updated_at = now or _iso_now()

    return {"version": LEDGER_VERSION, "updated_at": updated_at, "workspaces": new_ws}


def resolve_key_for_title(ledger: dict[str, Any] | None, title: str) -> str:
    """이슈 제목 → workspace_key 해석 (auto_dev_pipeline.sh automap 단일 소스).

    원장에서 title 의 접두사인 ticket_prefix 중 **가장 긴 것**을 고르고, 그 항목이
    `mapped`(repo_source 확보)일 때만 workspace_key 를 반환한다. 미매핑/원장 없음/
    pending_source(소스 미확보)는 빈 문자열 → 호출부(파이프라인)는 self-repo 로 진행한다.
    """
    if not ledger:
        return ""
    workspaces = ledger.get("workspaces") or {}
    best_prefix = ""
    best_key = ""
    for prefix, meta in workspaces.items():
        if (
            meta.get("status") == "mapped"
            and title.startswith(prefix)
            and len(prefix) > len(best_prefix)
        ):
            best_prefix = prefix
            best_key = meta.get("workspace_key") or ""
    return best_key


def write_ledger(path: str, ledger: dict[str, Any]) -> None:
    """원장을 원자적으로 쓴다(임시 파일 → rename). 상위 디렉터리 자동 생성."""
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def fetch_projects(api_url: str, service_key: str) -> list[dict[str, Any]]:
    """머신 조회 API 호출 → 프로젝트 목록. 실패 시 예외를 던진다(호출부가 흡수)."""
    url = api_url.rstrip("/") + MACHINE_PROJECTS_PATH
    req = urllib.request.Request(url, headers={"X-ClickEye-Service-Key": service_key})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — 신뢰된 내부 API
        data = json.load(resp)
    if not isinstance(data, list):
        raise ValueError(f"예상치 못한 응답(리스트 아님): {type(data).__name__}")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="인테이크→워크스페이스 매핑 원장 갱신")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_URL", "http://localhost:8000"),
        help="ClickEye API URL (기본: env API_URL 또는 http://localhost:8000)",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"원장 경로 (기본: {DEFAULT_OUTPUT})")
    parser.add_argument(
        "--dry-run", action="store_true", help="갱신 결과를 stdout 에 출력만 하고 파일은 쓰지 않는다"
    )
    parser.add_argument(
        "--resolve-title",
        metavar="TITLE",
        help="오프라인 해석 모드 — 원장(--output)에서 이 제목의 workspace_key 를 stdout 에 "
        "출력하고 종료(미매핑이면 빈 줄). 네트워크·서비스 키 불요. 파이프라인 automap 용.",
    )
    args = parser.parse_args(argv)

    # ── 오프라인 해석 모드 (파이프라인 automap): 원장 파일만 읽어 키를 출력한다. ──
    # 실패해도 파이프라인을 막지 않도록 항상 0 을 반환하고 빈 줄을 낸다(self-repo 폴백).
    if args.resolve_title is not None:
        ledger = load_ledger(args.output)
        print(resolve_key_for_title(ledger, args.resolve_title))
        return 0

    service_key = os.environ.get("CLICKEYE_SERVICE_KEY", "")
    if not service_key:
        print("ERROR: CLICKEYE_SERVICE_KEY 환경변수가 필요합니다.", file=sys.stderr)
        return 2

    try:
        projects = fetch_projects(args.api_url, service_key)
    except urllib.error.HTTPError as exc:
        print(f"ERROR: 머신 조회 실패 (HTTP {exc.code}): {exc.reason}", file=sys.stderr)
        return 1
    except (urllib.error.URLError, ValueError, OSError) as exc:
        print(f"ERROR: 머신 조회 실패: {exc}", file=sys.stderr)
        return 1

    existing = load_ledger(args.output)
    ledger = build_ledger(projects, existing)

    n_total = len(ledger["workspaces"])
    n_pending = sum(1 for v in ledger["workspaces"].values() if v["status"] == "pending_source")
    if args.dry_run:
        print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
        print(
            f"[DRY-RUN] 매핑 {n_total}건 (pending_source {n_pending}건) — 파일 미갱신",
            file=sys.stderr,
        )
        return 0

    write_ledger(args.output, ledger)
    print(
        f"매핑 원장 갱신: {args.output} — {n_total}건 (pending_source {n_pending}건)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
