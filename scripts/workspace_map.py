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


def resolve_project_for_key(ledger: dict[str, Any] | None, key: str) -> str:
    """workspace_key(또는 ticket_prefix) → project_id 해석.

    소비 토큰 원장(`llm_usage_ledger.project_id`)의 프로젝트 축을 파이프라인이 채우는 데 쓴다.
    이 축이 없으면 "프로젝트당 얼마 썼나" 를 집계할 수 없다(CE-362).

    수락 시 생성된 Project 의 id 는 이미 원장에 담겨 있으므로(machine/projects 폴링 산출물)
    서버를 다시 조회하지 않는다. 미매핑·원장 없음·project_id 부재는 빈 문자열 —
    호출부는 축 없이 진행한다(관측이 파이프라인을 막지 않는다).
    """
    if not ledger or not key:
        return ""
    workspaces = ledger.get("workspaces") or {}
    for prefix, meta in workspaces.items():
        if not isinstance(meta, dict):
            continue
        if key in (meta.get("workspace_key"), prefix, prefix.strip()):
            return str(meta.get("project_id") or "")
    return ""


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


def set_source(ledger: dict[str, Any], key: str, repo_source: str) -> dict[str, Any]:
    """원장 항목에 repo_source 를 수동 기입하고 status 를 mapped 로 전환한다(순수 함수).

    key 는 ticket_prefix(예: "[수주:3be49b62] ") 또는 workspace_key(예: "3be49b62")
    둘 중 하나로 매칭한다 — 먼저 workspaces 의 키(prefix)와 정확히 일치하는지 확인하고,
    없으면 각 항목의 workspace_key 필드와 일치하는 것을 찾는다.

    매칭되는 항목이 없으면 KeyError(항목을 새로 만들지 않는다 — 미존재 키는 에러로 거부).
    ledger["updated_at"] 은 건드리지 않는다 — 동일 호출을 반복해도 반환 dict 가 바이트
    단위로 동일해야 하는 멱등 요건은 이 함수가 updated_at 을 갱신하지 않음으로써 보장된다.
    """
    workspaces: dict[str, Any] = ledger.get("workspaces") or {}
    prefix = key if key in workspaces else None
    if prefix is None:
        for p, meta in workspaces.items():
            if meta.get("workspace_key") == key:
                prefix = p
                break
    if prefix is None:
        raise KeyError(f"워크스페이스를 찾을 수 없습니다: {key!r}")

    new_ws = dict(workspaces)
    entry = dict(new_ws[prefix])
    entry["repo_source"] = repo_source
    entry["status"] = "mapped"
    new_ws[prefix] = entry

    new_ledger = dict(ledger)
    new_ledger["workspaces"] = new_ws
    return new_ledger


def format_list(ledger: dict[str, Any] | None) -> str:
    """원장 상태 요약 — `--list` 용 사람이 읽기 쉬운 텍스트를 만든다(순수 함수).

    ticket_prefix 정렬 순으로 한 줄씩: prefix, workspace_key, status, repo_source 유무.
    원장이 없거나 workspaces 가 비어있으면 안내 문구 한 줄을 반환한다.
    """
    if not ledger:
        return "원장 없음"
    workspaces: dict[str, Any] = ledger.get("workspaces") or {}
    if not workspaces:
        return "원장에 워크스페이스 항목이 없습니다."
    lines = []
    for prefix in sorted(workspaces):
        meta = workspaces[prefix]
        repo_source = meta.get("repo_source")
        lines.append(
            f"{prefix} workspace_key={meta.get('workspace_key', '')} "
            f"status={meta.get('status', '')} repo_source={repo_source or '없음'}"
        )
    return "\n".join(lines)


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
    parser.add_argument(
        "--resolve-project",
        metavar="KEY",
        help="오프라인 해석 모드 — KEY(ticket_prefix 또는 workspace_key)의 project_id 를 "
        "stdout 에 출력하고 종료(미매핑이면 빈 줄). 소비 토큰 원장의 프로젝트 축 "
        "(CLICKEYE_PROJECT_ID)을 파이프라인이 채우는 데 쓴다. 네트워크·서비스 키 불요.",
    )
    parser.add_argument(
        "--set-source",
        nargs=2,
        metavar=("KEY", "REPO_SOURCE"),
        help="오프라인 기입 모드 — 원장(--output)에서 KEY(ticket_prefix 또는 workspace_key)로 "
        "찾은 항목에 REPO_SOURCE 를 기입하고 status 를 mapped 로 전환한다. 미존재 KEY 는 "
        "에러(항목을 새로 만들지 않음). 네트워크·서비스 키 불요.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="오프라인 조회 모드 — 원장(--output)의 워크스페이스 상태 요약을 stdout 에 출력하고 "
        "종료. 네트워크·서비스 키 불요.",
    )
    args = parser.parse_args(argv)

    # ── 오프라인 해석 모드 (파이프라인 automap): 원장 파일만 읽어 키를 출력한다. ──
    # 실패해도 파이프라인을 막지 않도록 항상 0 을 반환하고 빈 줄을 낸다(self-repo 폴백).
    if args.resolve_title is not None:
        ledger = load_ledger(args.output)
        print(resolve_key_for_title(ledger, args.resolve_title))
        return 0

    if args.resolve_project is not None:
        ledger = load_ledger(args.output)
        print(resolve_project_for_key(ledger, args.resolve_project))
        return 0

    # ── 오프라인 기입 모드: 원장 항목에 repo_source 를 수동 기입해 mapped 로 전환한다. ──
    if args.set_source is not None:
        key, repo_source = args.set_source
        ledger = load_ledger(args.output)
        if ledger is None:
            print(f"ERROR: 원장 파일이 없습니다: {args.output}", file=sys.stderr)
            return 2
        try:
            new_ledger = set_source(ledger, key, repo_source)
        except KeyError:
            print(f"ERROR: 워크스페이스를 찾을 수 없습니다: {key!r}", file=sys.stderr)
            return 2
        write_ledger(args.output, new_ledger)
        print(f"매핑 갱신: {key!r} → mapped (repo_source={repo_source})", file=sys.stderr)
        return 0

    # ── 오프라인 조회 모드: 원장 상태 요약을 출력한다(비차단 — 원장 없어도 0). ──
    if args.list:
        ledger = load_ledger(args.output)
        print(format_list(ledger))
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
