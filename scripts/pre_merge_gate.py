#!/usr/bin/env python3
"""ClickEye 자율 워크플로우 — 머지 직전 거버넌스 SSOT(Single Source of Truth) 게이트.

검증(정합성)과 위험분류를 한 모듈에 모은다. 두 곳에서 **동일하게** 호출된다:
  (a) auto_dev_pipeline.sh — git merge 직전, 권위(authoritative) 게이트.
      direct-merge + push origin main 이 유일한 비보호 경로이므로 여기가 진짜 관문이다.
  (b) .github/workflows/ci.yml — pull_request 미러. 같은 검증을 PR에서 재확인.

검증 항목(블로킹은 contract-drift / ticket-ref 둘뿐 — 수용기준 1):
  - contract-drift : API 계약면(app/api|schemas|models|ws, contracts/**)이 바뀌었는데
                     clickeye-contracts/openapi/openapi.json(또는 generated client)이 동반되지 않음 → 차단.
  - ticket-ref     : 브랜치 접미사 ralph/<KEY> 에서 이슈 키 추출, shape `^[A-Z0-9]+-\\d+$` 검증.
                     키 없으면(슬래시 없는 브랜치) skip→pass. 형태 불량이면 차단.
  - plan-trace     : .ralph/refined/<KEY>.md 또는 .ralph/PLAN.md 가 있으면 비자명성/연관성 점검(권고).
                     산출물이 없으면(CI 체크아웃 등) 자동 skip. 절대 블로킹하지 않음.

위험분류(머지경로 강등용 — 새 승인장치 없음):
  - HIGH : 변경 경로가 clickeye-contracts/** | clickeye-infra/** | **/*auth* | 보안키워드 → 직접머지 금지·PR 강등.
  - LOW  : 현행 유지.

토글(.env, pipeline_config.sh 와 동일 의미: 미설정=on, false/0/off/no=off):
  FLOWOPS_GOVERNANCE(마스터) / _CONTRACT / _TICKET / _TRACE / _RISK_DEMOTE

출력: --json 이면 결과 JSON. exit 0=pass, 2=fail(블로킹). 마스터 off면 항상 pass/LOW(회귀 0).

사용법:
  python3 scripts/pre_merge_gate.py --base main --head ralph/CE-123 --json
  python3 scripts/pre_merge_gate.py --base origin/main --head HEAD --ci --json   # CI 미러
  python3 scripts/pre_merge_gate.py --diff-files "clickeye-api/app/api/x.py" --head ralph/CE-1   # 테스트용
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 토글 ───────────────────────────────────────────────────────────────────
_FALSEY = {"false", "0", "off", "no"}


def is_enabled(key: str) -> bool:
    """pipeline_config.sh 의 is_enabled 과 동일 의미. 미설정/빈값은 on."""
    val = os.environ.get(key, "")
    if val == "":
        return True
    return val.strip().lower() not in _FALSEY


# ── 정책 상수 ──────────────────────────────────────────────────────────────
# API 계약면: 여기가 바뀌면 OpenAPI 스펙이 따라 갱신되어야 한다.
CONTRACT_SURFACE_PREFIXES = (
    "clickeye-api/app/api/",
    "clickeye-api/app/schemas/",
    "clickeye-api/app/models/",
    "clickeye-api/app/ws/",
)
OPENAPI_SPEC = "clickeye-contracts/openapi/openapi.json"
GENERATED_CLIENT_PREFIX = "clickeye-contracts/generated/"
CONTRACTS_PREFIX = "clickeye-contracts/"

# 위험(HIGH) 경로 — 변경 시 직접머지 금지, PR 경로로 강등.
HIGH_PREFIXES = (
    "clickeye-contracts/",
    "clickeye-infra/",
)
HIGH_PATH_PATTERNS = (
    re.compile(r"auth", re.IGNORECASE),
    re.compile(r"(secur|secret|crypto|password|token|rbac|permission|credential)", re.IGNORECASE),
)

ISSUE_KEY_RE = re.compile(r"^[A-Z0-9]+-\d+$")


# ── diff 수집 ──────────────────────────────────────────────────────────────
def get_changed_files(base: str, head: str) -> list[str]:
    """base...head(merge-base 기준) 변경 파일 목록. 실패 시 two-dot 폴백."""
    for spec in (f"{base}...{head}", f"{base}..{head}"):
        rc, out = _run(["git", "diff", "--name-only", spec])
        if rc == 0:
            return [f for f in out.splitlines() if f.strip()]
    return []


def _run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_DIR)
    return r.returncode, (r.stdout or "")


def extract_issue_key(head: str) -> str | None:
    """브랜치 접미사에서 이슈 키. ralph/CE-123 → CE-123. 슬래시 없으면 None(skip 대상)."""
    if "/" not in head:
        return None
    return head.rsplit("/", 1)[-1].strip() or None


# ── 검증기 ─────────────────────────────────────────────────────────────────
def check_contract_drift(files: list[str]) -> dict:
    """API 계약면 변경 ↔ openapi.json/generated client 동반 여부."""
    if not is_enabled("FLOWOPS_GOVERNANCE_CONTRACT"):
        return {"status": "skip", "detail": "FLOWOPS_GOVERNANCE_CONTRACT=off"}

    spec_touched = OPENAPI_SPEC in files
    generated_touched = any(f.startswith(GENERATED_CLIENT_PREFIX) for f in files)
    surface_changed = [f for f in files if f.startswith(CONTRACT_SURFACE_PREFIXES)]
    contracts_changed = [
        f
        for f in files
        if f.startswith(CONTRACTS_PREFIX)
        and f != OPENAPI_SPEC
        and not f.startswith(GENERATED_CLIENT_PREFIX)
    ]

    # API 계약면이 바뀌었는데 스펙이 안 따라옴 → drift
    if surface_changed and not spec_touched:
        return {
            "status": "fail",
            "detail": (
                "API 계약면 변경에 openapi.json 동반 없음(드리프트). "
                f"변경: {', '.join(surface_changed[:5])}"
            ),
        }
    # 계약 정의(protocol 등)가 바뀌었는데 생성 클라이언트가 안 따라옴 → drift
    if contracts_changed and not generated_touched:
        return {
            "status": "fail",
            "detail": (
                "contracts 변경에 generated 클라이언트 재생성 동반 없음. "
                f"변경: {', '.join(contracts_changed[:5])}"
            ),
        }
    if surface_changed or contracts_changed:
        return {"status": "pass", "detail": "계약면 변경에 스펙/클라이언트 동반 확인"}
    return {"status": "pass", "detail": "계약면 변경 없음"}


def check_ticket_ref(issue_key: str | None) -> dict:
    """브랜치에서 추출한 이슈 키의 형태 검증. 키 없으면 skip(pass)."""
    if not is_enabled("FLOWOPS_GOVERNANCE_TICKET"):
        return {"status": "skip", "detail": "FLOWOPS_GOVERNANCE_TICKET=off"}
    if not issue_key:
        return {"status": "skip", "detail": "브랜치에 이슈 키 없음 → skip"}
    if not ISSUE_KEY_RE.match(issue_key):
        return {
            "status": "fail",
            "detail": f"이슈 키 형태 불량: '{issue_key}' (기대 `^[A-Z0-9]+-\\d+$`)",
        }
    return {"status": "pass", "detail": f"이슈 키 {issue_key}"}


def check_plan_trace(issue_key: str | None, files: list[str]) -> dict:
    """정제 스펙/PLAN 존재 시 비자명성·연관성 점검(권고, 비블로킹). 없으면 skip."""
    if not is_enabled("FLOWOPS_GOVERNANCE_TRACE"):
        return {"status": "skip", "detail": "FLOWOPS_GOVERNANCE_TRACE=off"}

    candidates = []
    if issue_key:
        candidates.append(os.path.join(PROJECT_DIR, ".ralph", "refined", f"{issue_key}.md"))
    candidates.append(os.path.join(PROJECT_DIR, ".ralph", "PLAN.md"))

    plan_path = next((p for p in candidates if os.path.isfile(p)), None)
    if not plan_path:
        # CI 체크아웃 등 산출물 부재 → 미러에서 자동 skip
        return {"status": "skip", "detail": "PLAN/refined 산출물 없음 → skip"}

    try:
        content = open(plan_path, encoding="utf-8").read()
    except OSError as e:
        return {"status": "skip", "detail": f"plan 읽기 실패: {e}"}

    if len(content.strip()) < 80:
        return {"status": "warn", "detail": f"plan 내용 빈약({len(content.strip())}자): {plan_path}"}

    # 변경된 최상위 영역이 plan에 한 번도 언급되지 않으면 경고(연관성 약함)
    top_dirs = {f.split("/", 1)[0] for f in files if "/" in f}
    unref = [d for d in top_dirs if d and d not in content]
    if top_dirs and len(unref) == len(top_dirs):
        return {
            "status": "warn",
            "detail": f"plan이 변경 영역({', '.join(sorted(top_dirs))})을 언급하지 않음",
        }
    return {"status": "pass", "detail": f"plan 추적 확인: {os.path.relpath(plan_path, PROJECT_DIR)}"}


# ── 위험분류 ───────────────────────────────────────────────────────────────
def classify_risk(files: list[str]) -> dict:
    reasons = []
    for f in files:
        if f.startswith(HIGH_PREFIXES):
            reasons.append(f)
            continue
        for pat in HIGH_PATH_PATTERNS:
            if pat.search(f):
                reasons.append(f)
                break
    tier = "HIGH" if reasons else "LOW"
    return {"tier": tier, "reasons": sorted(set(reasons))[:10]}


# ── 종합 ───────────────────────────────────────────────────────────────────
def evaluate(base: str, head: str, files: list[str] | None = None) -> dict:
    issue_key = extract_issue_key(head)

    # 마스터 off → 거버넌스 우회(회귀 0)
    if not is_enabled("FLOWOPS_GOVERNANCE"):
        return {
            "governance": "off",
            "issue_key": issue_key,
            "tier": "LOW",
            "checks": {},
            "failures": [],
            "warnings": [],
            "verdict": "pass",
            "merge_decision": "direct",
        }

    if files is None:
        files = get_changed_files(base, head)

    checks = {
        "contract_drift": check_contract_drift(files),
        "ticket_ref": check_ticket_ref(issue_key),
        "plan_trace": check_plan_trace(issue_key, files),
    }
    risk = classify_risk(files)
    tier = risk["tier"]

    # 블로킹: contract-drift / ticket-ref 만 (plan-trace 는 권고)
    failures = [
        f"{name}: {c['detail']}"
        for name, c in checks.items()
        if name in ("contract_drift", "ticket_ref") and c["status"] == "fail"
    ]
    warnings = [
        f"{name}: {c['detail']}" for name, c in checks.items() if c["status"] == "warn"
    ]

    if failures:
        verdict, merge_decision = "fail", "block"
    elif tier == "HIGH" and is_enabled("FLOWOPS_GOVERNANCE_RISK_DEMOTE"):
        verdict, merge_decision = "pass", "pr"
    else:
        verdict, merge_decision = "pass", "direct"

    return {
        "governance": "on",
        "issue_key": issue_key,
        "tier": tier,
        "risk_reasons": risk["reasons"],
        "checks": checks,
        "failures": failures,
        "warnings": warnings,
        "verdict": verdict,
        "merge_decision": merge_decision,
        "changed_files": len(files),
    }


def main() -> int:
    p = argparse.ArgumentParser(description="ClickEye 머지 전 거버넌스 게이트(SSOT)")
    p.add_argument("--base", default="main", help="기준 ref (기본 main)")
    p.add_argument("--head", default="HEAD", help="대상 ref/브랜치 (기본 HEAD)")
    p.add_argument("--ci", action="store_true", help="CI 미러 모드(표기용)")
    p.add_argument("--json", action="store_true", help="결과 JSON 출력")
    p.add_argument(
        "--diff-files",
        default=None,
        help="git 대신 사용할 변경 파일 목록(콤마/줄바꿈 구분, 테스트용)",
    )
    args = p.parse_args()

    files = None
    if args.diff_files is not None:
        files = [f.strip() for f in re.split(r"[,\n]", args.diff_files) if f.strip()]

    result = evaluate(args.base, args.head, files)

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"[governance:{result['governance']}] verdict={result['verdict']} "
              f"tier={result['tier']} merge={result['merge_decision']} "
              f"key={result['issue_key']}")
        for f in result["failures"]:
            print(f"  ❌ {f}", file=sys.stderr)
        for w in result["warnings"]:
            print(f"  ⚠️  {w}", file=sys.stderr)

    return 2 if result["verdict"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
