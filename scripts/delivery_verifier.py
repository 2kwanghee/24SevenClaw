#!/usr/bin/env python3
"""딜리버리 정합성 검증기 (다프로젝트화 P7) — 완주 판정 + 프로젝트 게이트 실행.

검증 배치(scripts/delivery_verify.sh)가 호출한다. 두 가지 일만 한다:

1. **완주 판정** — 발급 원장(P6 `intake.tickets`)의 issue_id 전량을 Linear 상태와
   대조한다. 기준은 linear_watcher 와 동일한 TERMINAL_STATES:
     - Done                → 완료
     - Canceled/Duplicate  → 완주로 **인정하되 리포트에 명시**(구현 없이 닫힌 티켓이
                             숨지 않도록 — 서비스 #2 가 판단 근거를 가진다)
     - 그 외(Queued/In Progress/Backlog…) → 미완주. 게이트를 실행하지 않는다.
2. **게이트 실행** — 제어면 YAML `gates`(P2)에서 온 명령을 프로젝트 워크스페이스에서
   순차 실행한다. 전부 exit 0 이어야 통과. **전 게이트를 실행해 결과를 모은다**
   (fail-fast 로 뒤 게이트의 실패를 숨기지 않는다 — 리포트가 수리 계획의 입력이다).

## exit 계약 (배치가 이 코드로 분기한다)

  0 = 완주 + 게이트 전량 통과  → 배치가 passed=true 로 POST /verified
  3 = 미완주(잔존 티켓 있음)    → 배치 skip, 다음 주기 재확인
  4 = 완주 + 게이트 실패        → 배치가 passed=false 로 POST /verified
  5 = 게이트 명령 부재          → **검증 불가** — verified 전이 금지(통과 위장 금지),
                                  배치는 관측 로그만 남긴다
  2 = 입력 오류(원장/게이트 파일 불량)

stdout 은 결과 JSON({verdict, complete, passed, report}) 하나만 — 배치가 report 를
그대로 서버에 전달한다(report 는 증거다 — 서버 스키마가 빈 report 를 거부한다).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any

sys.path.insert(0, "scripts")

from linear_client import get_env, linear_request  # noqa: E402

# 완주 판정은 **state type 기준**이다(E2E 실증 결함 수정): 팀마다 완료 상태의
# 이름이 다르다 — 예: ClickEye 팀은 Done 외에 Confirm(type=completed)을 쓴다.
# 이름 기준이면 Confirm 으로 옮겨진 티켓이 영구 미완주가 된다.
# 이름 셋은 type 정보가 없는 입력(레거시/테스트 주입)의 폴백이다.
DONE_TYPES = frozenset({"completed"})
ABSORBED_TYPES = frozenset({"canceled", "duplicate"})
DONE_STATES = frozenset({"Done", "Confirm"})
ABSORBED_STATES = frozenset({"Canceled", "Duplicate"})
TERMINAL_STATES = DONE_STATES | ABSORBED_STATES

GATE_TIMEOUT_DEFAULT = 1800  # 게이트 1개당 초 — 통합 테스트는 길다
REPORT_MAX = 20000  # 서버 VerificationRecordRequest.report 상한과 일치
_TAIL_LINES = 30  # 게이트 실패 시 리포트에 싣는 출력 꼬리
# 게이트 1개 tail 의 문자 상한 — 한 게이트의 거대한 출력(예: 한 줄 수만 자)이 전체
# 상한(REPORT_MAX) 절단으로 **뒤 게이트의 요약 줄을 밀어내는** 것을 막는다.
# 요약 줄(✅/❌ exit 코드)이 전부 살아남는 것이 개별 로그 전문보다 우선이다.
_TAIL_CHARS = 3000

EXIT_VERIFIED = 0
EXIT_INCOMPLETE = 3
EXIT_GATE_FAILED = 4
EXIT_NO_GATES = 5


# ── 1) 완주 판정 (순수 — 테스트는 상태 dict 를 직접 주입) ─────────────────────


def classify_completion(
    ledger: list[dict[str, Any]], states_by_id: dict[str, Any]
) -> dict[str, Any]:
    """원장 × Linear 상태 → 완주 분류. 미지 issue_id(조회 실패)는 잔존으로 취급한다
    — 상태를 모르는 티켓을 완료로 가정하면 미완주가 통과로 위장된다(fail-closed).

    상태 값은 `{"name": …, "type": …}` dict(fetch_states 산출) 또는 이름 문자열
    (레거시/테스트 주입)을 받는다. **type 이 있으면 type 이 우선**한다 — 팀별
    상태명 커스텀(예: Confirm=completed)에 견고해야 한다(E2E 실증).
    """
    done: list[str] = []
    absorbed: list[str] = []
    remaining: list[dict[str, str]] = []
    for t in ledger:
        raw = states_by_id.get(t["issue_id"])
        if isinstance(raw, dict):
            name = raw.get("name") or ""
            stype = raw.get("type") or ""
        else:
            name, stype = (raw or ""), ""
        ident = t.get("identifier", t["issue_id"])

        if (stype in DONE_TYPES) or (not stype and name in DONE_STATES):
            done.append(ident)
        elif (stype in ABSORBED_TYPES) or (not stype and name in ABSORBED_STATES):
            absorbed.append(f"{ident}({name})")
        else:
            remaining.append({"identifier": ident, "state": name or "UNKNOWN"})
    return {
        "complete": not remaining,
        "done": done,
        "absorbed": absorbed,
        "remaining": remaining,
        "total": len(ledger),
    }


def fetch_states(issue_ids: list[str]) -> dict[str, dict[str, str]]:
    """Linear 에서 issue_id → {name, type} 조회. 조회 누락분은 classify 가 잔존 처리.

    type 을 함께 가져오는 이유: 완주 판정은 type 기준이다(classify_completion 참조).
    """
    api_key, _team_id = get_env()
    query = """
    query($ids: [ID!]!) {
        issues(filter: { id: { in: $ids } }) {
            nodes { id state { name type } }
        }
    }
    """
    data = linear_request(api_key, query, {"ids": issue_ids}) or {}
    nodes = ((data.get("issues") or {}).get("nodes")) or []
    return {
        n["id"]: {
            "name": ((n.get("state") or {}).get("name") or ""),
            "type": ((n.get("state") or {}).get("type") or ""),
        }
        for n in nodes
    }


# ── 2) 게이트 실행 ───────────────────────────────────────────────────────────


def run_gates(
    commands: list[str], *, workdir: str, timeout: int = GATE_TIMEOUT_DEFAULT
) -> list[dict[str, Any]]:
    """게이트 명령을 순차 실행하고 전 결과를 모은다(중도 포기 없음 — 리포트 완전성).

    각 결과: {cmd, exit, timed_out, tail}. tail 은 stdout+stderr 병합의 마지막
    _TAIL_LINES 줄 — 실패 원인이 리포트에 남는 최소 증거다.
    """
    results: list[dict[str, Any]] = []
    for cmd in commands:
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            merged = (proc.stdout or "") + (proc.stderr or "")
            results.append({
                "cmd": cmd,
                "exit": proc.returncode,
                "timed_out": False,
                "tail": "\n".join(merged.splitlines()[-_TAIL_LINES:]),
            })
        except subprocess.TimeoutExpired:
            results.append({
                "cmd": cmd,
                "exit": -1,
                "timed_out": True,
                "tail": f"(타임아웃 {timeout}s — 게이트 미완료는 실패다)",
            })
    return results


# ── 3) 리포트 (증거 — 서버가 빈 리포트를 거부한다) ──────────────────────────


def build_report(completion: dict[str, Any], gate_results: list[dict[str, Any]]) -> str:
    lines = [
        f"완주: {len(completion['done'])}/{completion['total']} Done"
        + (f" · 흡수 {len(completion['absorbed'])}건({', '.join(completion['absorbed'])})"
           if completion["absorbed"] else ""),
    ]
    if completion["remaining"]:
        lines.append("잔존: " + ", ".join(
            f"{r['identifier']}={r['state']}" for r in completion["remaining"]
        ))
    for g in gate_results:
        mark = "✅" if g["exit"] == 0 else "❌"
        lines.append(f"{mark} gate `{g['cmd']}` → exit {g['exit']}"
                     + (" (timeout)" if g["timed_out"] else ""))
        if g["exit"] != 0 and g["tail"]:
            tail = g["tail"]
            if len(tail) > _TAIL_CHARS:
                # 양끝 보존 — 실패 원인 요약은 머리(첫 에러 메시지)에도 꼬리(최종
                # 집계)에도 올 수 있다. 가운데를 접는 것이 정보 손실이 가장 적다.
                head_n = _TAIL_CHARS // 3
                tail = tail[:head_n] + "\n…(중간 절단)…\n" + tail[-(_TAIL_CHARS - head_n):]
            lines.append(tail)
    return "\n".join(lines)[:REPORT_MAX]


# ── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser(description="완주 판정 + 정합성 게이트 실행 (P7)")
    p.add_argument("--ledger", required=True, help="발급 원장 JSON 파일 ([{issue_id,...}])")
    p.add_argument("--gates-file", default=None,
                   help="게이트 명령 파일(줄당 1명령, # 주석 허용). 없거나 비면 exit 5")
    p.add_argument("--workdir", default=".", help="게이트 실행 워크스페이스")
    p.add_argument("--gate-timeout", type=int, default=GATE_TIMEOUT_DEFAULT)
    p.add_argument("--check-only", action="store_true",
                   help="완주 판정만(게이트 미실행) — 상태 관측용")
    args = p.parse_args()

    try:
        ledger = json.load(open(args.ledger, encoding="utf-8"))
        if isinstance(ledger, dict):
            ledger = ledger.get("tickets") or []
        if not isinstance(ledger, list) or not ledger or any(
            not isinstance(t, dict) or not t.get("issue_id") for t in ledger
        ):
            raise ValueError("원장은 issue_id 를 가진 객체 배열이어야 함")
    except (OSError, json.JSONDecodeError, ValueError) as e:
        print(f"[verifier] 원장 불량: {e}", file=sys.stderr)
        return 2

    states = fetch_states([t["issue_id"] for t in ledger])
    completion = classify_completion(ledger, states)

    if not completion["complete"]:
        print(json.dumps({
            "verdict": "incomplete", "complete": False, "passed": None,
            "report": build_report(completion, []),
        }, ensure_ascii=False))
        return EXIT_INCOMPLETE

    if args.check_only:
        print(json.dumps({
            "verdict": "complete", "complete": True, "passed": None,
            "report": build_report(completion, []),
        }, ensure_ascii=False))
        return EXIT_VERIFIED

    # 게이트 명령 로드 — 부재는 "통과"가 아니라 "검증 불가"다.
    commands: list[str] = []
    if args.gates_file:
        try:
            with open(args.gates_file, encoding="utf-8") as fh:
                commands = [
                    line.strip() for line in fh
                    if line.strip() and not line.strip().startswith("#")
                ]
        except OSError as e:
            print(f"[verifier] 게이트 파일 불량: {e}", file=sys.stderr)
            return 2
    if not commands:
        print(json.dumps({
            "verdict": "no_gates", "complete": True, "passed": None,
            "report": build_report(completion, []) + "\n⚠️ 게이트 명령 부재 — 검증 불가(통과 위장 금지)",
        }, ensure_ascii=False))
        return EXIT_NO_GATES

    gate_results = run_gates(commands, workdir=args.workdir, timeout=args.gate_timeout)
    passed = all(g["exit"] == 0 for g in gate_results)
    print(json.dumps({
        "verdict": "verified" if passed else "gate_failed",
        "complete": True,
        "passed": passed,
        "report": build_report(completion, gate_results),
    }, ensure_ascii=False))
    return EXIT_VERIFIED if passed else EXIT_GATE_FAILED


if __name__ == "__main__":
    sys.exit(main())
