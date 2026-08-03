#!/usr/bin/env python3
"""seat_map.py — 로컬 시트 풀 원장 (다프로젝트화 P5/CE-345).

워크스페이스별 전용 러너가 **자기 구독 시트(계정)** 로 `claude` 를 실행하도록,
시트 등재 · 워크스페이스 배정 · 파이프라인용 오프라인 해석을 담당한다.
원장은 `.ralph/seats.json`(git 미추적) 이며, 토큰 **값**은 절대 담지 않는다 —
시트 인증은 토큰 파일 경로 또는 CLI 설정 디렉터리 경로로만 기술한다.

원장 스키마:
  {
    "version": 1,
    "updated_at": "2026-08-03T00:00:00Z",
    "seats": {
      "seat-a": {
        "seat_id": "seat-a",
        "label": "자유 텍스트",
        "auth": {"oauth_token_file": ".ralph/seats/seat-a.token"},
        "status": "active" | "pending_login" | "disabled",
        "note": ""
      }
    },
    "assignments": {"3be49b62": "seat-a"}
  }

설계 원칙:
- **비밀 미보유**: 원장에도 stdout 에도 토큰 값은 나오지 않는다(경로만). 파일→env 주입은
  호출부(auto_dev_pipeline.sh `apply_seat_env`)가 수행한다.
- **매핑 원장과 분리**: `.ralph/workspaces.json`(workspace_map.py)은 읽지도 쓰지도 않는다.
  assignments 의 키는 그저 workspace_key 문자열이며, 두 원장은 독립적으로 갱신된다.
- **1시트:1워크스페이스**: 한 시트를 둘 이상의 워크스페이스에 배정하면 같은 계정으로 동시
  실행이 나므로 `--force` 없이는 거부한다(다계정 동시 실행의 전제).
- **멱등**: 같은 입력 2회 = 동일 결과. seats/assignments 가 변하지 않으면 updated_at 도
  유지해 파일이 바이트 단위로 동일하다.
- **비차단 해석**: `resolve` 는 항상 exit 0 — 미배정·비active·인증 파일 부재는 빈 출력이며,
  호출부는 현행 로그인 세션으로 폴백한다(회귀 0).

stdlib 만 사용(외부 의존 없음). 네트워크 호출 없음 — 전 서브커맨드가 오프라인 동작.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from datetime import UTC, datetime
from typing import Any

DEFAULT_OUTPUT = ".ralph/seats.json"
LEDGER_VERSION = 1
VALID_STATUSES = ("active", "pending_login", "disabled")
# 시트 ID 는 파일 경로(`.ralph/.seat_lock.<seat_id>`)와 셸 변수 값으로 합성되므로 문자를 제한한다.
SEAT_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def validate_seat_id(seat_id: str) -> str:
    """시트 ID 형식 검증 — 경로 합성 오염(슬래시·공백·메타문자) 차단."""
    if not seat_id or not SEAT_ID_RE.match(seat_id):
        raise ValueError(
            f"허용되지 않는 seat_id: {seat_id!r} (영숫자 및 '_', '.', '-' 만 사용)"
        )
    return seat_id


def _iso_now() -> str:
    """ISO8601 Z(초 단위) — 원장 updated_at 포맷(workspace_map 과 동일 규약)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def empty_ledger(now: str | None = None) -> dict[str, Any]:
    """빈 원장(신규 생성 경로)."""
    return {
        "version": LEDGER_VERSION,
        "updated_at": now or _iso_now(),
        "seats": {},
        "assignments": {},
    }


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


def stamp(existing: dict[str, Any] | None, ledger: dict[str, Any], now: str | None = None) -> dict[str, Any]:
    """멱등 타임스탬프 — seats/assignments 가 기존과 같으면 updated_at 을 유지한다.

    변경 함수(register_seat/assign/set_status)는 updated_at 을 건드리지 않는 순수 함수이며,
    쓰기 직전 이 함수가 한 번만 시각을 찍는다. 내용 불변 시 파일이 바이트 단위로 동일해진다.
    """
    existing = existing or {}
    unchanged = (
        existing.get("version") == LEDGER_VERSION
        and (existing.get("seats") or {}) == (ledger.get("seats") or {})
        and (existing.get("assignments") or {}) == (ledger.get("assignments") or {})
    )
    updated_at = existing.get("updated_at") if unchanged else None
    return {
        "version": LEDGER_VERSION,
        "updated_at": updated_at or now or _iso_now(),
        "seats": ledger.get("seats") or {},
        "assignments": ledger.get("assignments") or {},
    }


def register_seat(
    ledger: dict[str, Any],
    seat_id: str,
    token_file: str | None = None,
    config_dir: str | None = None,
    label: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """시트를 등재/갱신한다(순수 함수 — 원본 불변, updated_at 미변경).

    기존 항목의 수동 값(label/note/auth/status)은 인자로 덮어쓰지 않는 한 보존한다.
    인증 수단(oauth_token_file / config_dir)이 하나도 없으면 status 는 pending_login 강제 —
    로그인 전 시트에 배정만 걸려 조용히 기본 세션으로 도는 것을 막는다.
    """
    validate_seat_id(seat_id)
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(f"허용되지 않는 status: {status!r}")

    seats: dict[str, Any] = dict(ledger.get("seats") or {})
    prev: dict[str, Any] = dict(seats.get(seat_id) or {})
    auth: dict[str, Any] = dict(prev.get("auth") or {})
    if token_file:
        auth["oauth_token_file"] = token_file
    if config_dir:
        auth["config_dir"] = config_dir

    if not auth:
        new_status = "pending_login"  # 인증 미확보 → 배정돼도 해석되지 않는다
    else:
        new_status = status or prev.get("status") or "active"

    seats[seat_id] = {
        "seat_id": seat_id,
        "label": label if label is not None else prev.get("label", ""),
        "auth": auth,
        "status": new_status,
        "note": prev.get("note", ""),
    }
    new_ledger = dict(ledger)
    new_ledger["seats"] = seats
    return new_ledger


def assign(
    ledger: dict[str, Any], workspace_key: str, seat_id: str, force: bool = False
) -> dict[str, Any]:
    """워크스페이스에 시트를 배정한다(순수 함수 — 원본 불변, updated_at 미변경).

    - 미등재 시트 → KeyError(배정만으로 시트를 창작하지 않는다).
    - 해당 시트가 이미 **다른** workspace_key 에 배정돼 있으면 --force 없이 ValueError —
      한 계정이 두 러너에서 동시에 돌면 시트 축 원장과 레이트 한도가 모두 거짓이 된다.
    """
    if not workspace_key:
        raise ValueError("workspace_key 가 비어 있습니다.")
    validate_seat_id(seat_id)
    seats: dict[str, Any] = ledger.get("seats") or {}
    if seat_id not in seats:
        raise KeyError(f"등재되지 않은 시트: {seat_id!r}")

    assignments: dict[str, Any] = dict(ledger.get("assignments") or {})
    if not force:
        held = [k for k, v in assignments.items() if v == seat_id and k != workspace_key]
        if held:
            raise ValueError(
                f"시트 {seat_id!r} 는 이미 워크스페이스 {held[0]!r} 에 배정돼 있습니다"
                " (1시트:1워크스페이스 — 재배정하려면 --force)"
            )
    assignments[workspace_key] = seat_id

    new_ledger = dict(ledger)
    new_ledger["assignments"] = assignments
    return new_ledger


def set_status(ledger: dict[str, Any], seat_id: str, status: str) -> dict[str, Any]:
    """시트 상태를 변경한다(순수 함수). 미등재 시트는 KeyError, 미허용 상태는 ValueError."""
    if status not in VALID_STATUSES:
        raise ValueError(f"허용되지 않는 status: {status!r} (허용: {', '.join(VALID_STATUSES)})")
    seats: dict[str, Any] = dict(ledger.get("seats") or {})
    if seat_id not in seats:
        raise KeyError(f"등재되지 않은 시트: {seat_id!r}")
    entry = dict(seats[seat_id])
    entry["status"] = status
    seats[seat_id] = entry

    new_ledger = dict(ledger)
    new_ledger["seats"] = seats
    return new_ledger


def base_dir_for(path: str) -> str:
    """원장 기재 **상대경로**의 기준 디렉터리 — `<repo>/.ralph/seats.json` 이면 `<repo>`.

    해석 결과를 소비하는 파이프라인 STEP B 는 워크스페이스로 cd 한 뒤 실행하므로, 상대경로를
    호출자 cwd 기준으로 두면 인증 파일을 놓친다. 기준을 원장 위치로 고정해 cwd 무관하게 만든다.
    """
    parent = os.path.dirname(os.path.abspath(path))
    if os.path.basename(parent) == ".ralph":
        return os.path.dirname(parent)
    return parent


def _resolve_path(base: str, value: str) -> str:
    """원장 기재 경로 → 절대경로(상대경로는 base 기준). 이미 절대경로면 그대로."""
    if os.path.isabs(value):
        return os.path.normpath(value)
    return os.path.normpath(os.path.join(base, value))


def resolve_seat_env(
    ledger: dict[str, Any] | None, workspace_key: str, base: str
) -> list[str]:
    """워크스페이스 → 셸 eval 가능한 시트 환경 기술(파이프라인 전용, 비차단).

    다음을 **전부** 충족할 때만 줄 목록을 반환하고, 아니면 빈 목록(→ 기본 세션 폴백):
      배정 존재 → 시트 등재 → status == "active" → 인증 실체(파일/디렉터리)가 **판독 가능**.
    출력은 `SEAT_ID` + (`SEAT_TOKEN_FILE` | `SEAT_CONFIG_DIR`) 이며 **경로만** 담는다 —
    토큰 값은 이 프로세스가 읽지도 출력하지도 않는다.

    예외적으로 배정 시트가 `disabled`(운영자가 한도도달·차단으로 내림) 이면 `SEAT_BLOCKED=disabled`
    한 줄을 낸다 — 이 경우 기본 계정 폴백은 곧 원장 오귀속이므로 호출부가 단계를 막아야 한다.
    """
    if not ledger or not workspace_key:
        return []
    assignments: dict[str, Any] = ledger.get("assignments") or {}
    seat_id = assignments.get(workspace_key)
    if not seat_id:
        return []
    seat: dict[str, Any] = (ledger.get("seats") or {}).get(seat_id) or {}
    status = seat.get("status")
    if status == "disabled":
        return ["SEAT_BLOCKED=disabled"]
    if status != "active":
        return []

    auth: dict[str, Any] = seat.get("auth") or {}
    token_file = auth.get("oauth_token_file")
    if token_file:
        abs_token = _resolve_path(base, str(token_file))
        # 존재만으로는 부족하다 — 읽히지 않는 파일은 "시트 확보"가 아니다(호출부 오귀속 방지).
        if os.path.isfile(abs_token) and os.access(abs_token, os.R_OK):
            return [
                f"SEAT_ID={shlex.quote(str(seat_id))}",
                f"SEAT_TOKEN_FILE={shlex.quote(abs_token)}",
            ]
    config_dir = auth.get("config_dir")
    if config_dir:
        abs_dir = _resolve_path(base, str(config_dir))
        if os.path.isdir(abs_dir) and os.access(abs_dir, os.R_OK | os.X_OK):
            return [
                f"SEAT_ID={shlex.quote(str(seat_id))}",
                f"SEAT_CONFIG_DIR={shlex.quote(abs_dir)}",
            ]
    return []


def format_list(ledger: dict[str, Any] | None) -> str:
    """시트/배정 요약 — `list` 용 사람이 읽는 텍스트(순수 함수, 토큰 값 미출력)."""
    if not ledger:
        return "원장 없음"
    seats: dict[str, Any] = ledger.get("seats") or {}
    assignments: dict[str, Any] = ledger.get("assignments") or {}
    if not seats and not assignments:
        return "원장에 시트 항목이 없습니다."

    # 시트 → 배정된 워크스페이스 역인덱스(1시트:1워크스페이스가 원칙이나 --force 대비 목록).
    reverse: dict[str, list[str]] = {}
    for ws_key, seat_id in assignments.items():
        reverse.setdefault(str(seat_id), []).append(str(ws_key))

    lines = ["[시트]"]
    for seat_id in sorted(seats):
        meta = seats[seat_id] or {}
        auth = meta.get("auth") or {}
        auth_desc = auth.get("oauth_token_file") or auth.get("config_dir") or "없음"
        ws_desc = ", ".join(sorted(reverse.get(seat_id, []))) or "미배정"
        label = meta.get("label") or ""
        lines.append(
            f"  {seat_id} status={meta.get('status', '')} auth={auth_desc} "
            f"workspace={ws_desc}" + (f" label={label}" if label else "")
        )
    lines.append("[배정]")
    if assignments:
        for ws_key in sorted(assignments, key=str):
            seat_id = str(assignments[ws_key])
            known = "" if seat_id in seats else " (미등재 시트!)"
            lines.append(f"  {ws_key} → {seat_id}{known}")
    else:
        lines.append("  (없음)")
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


def _save(path: str, existing: dict[str, Any] | None, ledger: dict[str, Any]) -> None:
    """멱등 타임스탬프 후 원자적 쓰기."""
    write_ledger(path, stamp(existing, ledger))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="로컬 시트 풀 원장 관리 (CE-345)")
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT, help=f"원장 경로 (기본: {DEFAULT_OUTPUT})"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_reg = sub.add_parser("register-seat", help="시트 등재/갱신")
    p_reg.add_argument("--id", dest="seat_id", required=True, help="시트 ID (예: seat-a)")
    p_reg.add_argument(
        "--token-file", help="OAuth 토큰 파일 경로(권장). 원장 상대경로는 레포 루트 기준"
    )
    p_reg.add_argument("--config-dir", help="CLI 설정 디렉터리 경로(폴백, CLAUDE_CONFIG_DIR)")
    p_reg.add_argument("--label", help="사람이 읽는 설명(계정 별칭 등)")
    p_reg.add_argument(
        "--status", choices=VALID_STATUSES, help="상태 (기본: 인증 확보 시 active)"
    )
    p_reg.add_argument("--output", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    p_asg = sub.add_parser("assign", help="워크스페이스에 시트 배정")
    p_asg.add_argument("--workspace", required=True, help="workspace_key")
    p_asg.add_argument("--seat", required=True, help="시트 ID(등재돼 있어야 한다)")
    p_asg.add_argument(
        "--force", action="store_true", help="이미 다른 워크스페이스에 배정된 시트를 재배정"
    )
    p_asg.add_argument("--output", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    p_st = sub.add_parser("set-status", help="시트 상태 변경(한도도달 시 disabled 등)")
    p_st.add_argument("--seat", required=True, help="시트 ID")
    p_st.add_argument("--status", required=True, choices=VALID_STATUSES, help="변경할 상태")
    p_st.add_argument("--output", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    p_ls = sub.add_parser("list", help="시트/배정 요약 출력(토큰 값 미출력 — 경로만)")
    p_ls.add_argument("--output", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    p_rs = sub.add_parser(
        "resolve", help="파이프라인용 오프라인 해석 — 셸 eval 가능한 시트 환경 출력(항상 exit 0)"
    )
    p_rs.add_argument("--resolve-key", required=True, help="workspace_key")
    p_rs.add_argument("--output", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    # 서브파서에도 --output 을 두어 `... resolve --resolve-key K --output P` 순서를 허용한다.
    output = getattr(args, "output", None) or DEFAULT_OUTPUT

    existing = load_ledger(output)

    # ── 해석 모드: 파이프라인이 매 실행 호출한다. 어떤 이유로도 실패시키지 않는다. ──
    if args.command == "resolve":
        for line in resolve_seat_env(existing, args.resolve_key, base_dir_for(output)):
            print(line)
        return 0

    if args.command == "list":
        print(format_list(existing))
        return 0

    ledger = existing if existing is not None else empty_ledger()

    if args.command == "register-seat":
        try:
            new_ledger = register_seat(
                ledger,
                args.seat_id,
                token_file=args.token_file,
                config_dir=args.config_dir,
                label=args.label,
                status=args.status,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        _save(output, existing, new_ledger)
        entry = new_ledger["seats"][args.seat_id]
        print(f"시트 등재: {args.seat_id} (status={entry['status']})", file=sys.stderr)
        if entry["status"] == "pending_login":
            print(
                "  인증 경로 미기입 — `claude setup-token` 후 --token-file 로 재등재하세요.",
                file=sys.stderr,
            )
        return 0

    if args.command == "assign":
        try:
            new_ledger = assign(ledger, args.workspace, args.seat, force=args.force)
        except KeyError as exc:
            print(f"ERROR: {exc.args[0]}", file=sys.stderr)
            return 2
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        _save(output, existing, new_ledger)
        print(f"배정: 워크스페이스 {args.workspace} → 시트 {args.seat}", file=sys.stderr)
        return 0

    if args.command == "set-status":
        try:
            new_ledger = set_status(ledger, args.seat, args.status)
        except KeyError as exc:
            print(f"ERROR: {exc.args[0]}", file=sys.stderr)
            return 2
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        _save(output, existing, new_ledger)
        print(f"상태 변경: 시트 {args.seat} → {args.status}", file=sys.stderr)
        return 0

    parser.error(f"알 수 없는 서브커맨드: {args.command}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
