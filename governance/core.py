"""ClickEye 거버넌스 커널 — 머지 직전 검증(정합성)·위험분류 순수 로직(SSOT).

이 모듈은 **stdlib 전용**(argparse/json/os/re/subprocess/sys)이며 의존성이 0이다.
파이프라인(auto_dev_pipeline.sh)과 CI(ci.yml)가 시스템 python3 로 설치 없이 저장소
루트에서 호출하므로, 여기에 FastAPI/pydantic 등 제3자 패키지를 절대 import 하지 않는다.

원래 scripts/pre_merge_gate.py 의 순수 본문을 이곳으로 이전했다. 판정 로직·토글·상수·
정규식은 동작이 동일하다. 단, 경로 의존(PROJECT_DIR) 부분만 `project_dir`
인자로 매개변수화하여 (a) 로컬/CI 는 저장소 루트를, (b) 원격 HTTP 는 None(=git/.ralph
미접근, plan-trace skip)을 넘길 수 있게 했다.

검증 항목(블로킹은 contract-drift / ticket-ref 둘뿐):
  - contract-drift : API 계약면 변경에 openapi.json/generated 동반 없으면 차단.
  - ticket-ref     : 브랜치 접미사 ralph/<KEY> 형태 검증. 없으면 skip, 불량이면 차단.
  - plan-trace     : .ralph/refined/<KEY>.md 또는 PLAN.md 존재 시 연관성 점검(권고, 비블로킹).

위험분류(머지경로 강등용): HIGH(contracts/infra/auth/보안) → 직접머지 금지·PR 강등.
"""

from __future__ import annotations

import os
import re
import subprocess

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
def _run(cmd: list[str], cwd: str) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return r.returncode, (r.stdout or "")


def get_changed_files(base: str, head: str, *, project_dir: str) -> list[str]:
    """base...head(merge-base 기준) 변경 파일 목록. 실패 시 two-dot 폴백.

    git 은 `project_dir` 에서 실행한다(파이프라인·CI 는 저장소 루트).
    """
    for spec in (f"{base}...{head}", f"{base}..{head}"):
        rc, out = _run(["git", "diff", "--name-only", spec], cwd=project_dir)
        if rc == 0:
            return [f for f in out.splitlines() if f.strip()]
    return []


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


def check_plan_trace(
    issue_key: str | None,
    files: list[str],
    *,
    project_dir: str | None = None,
    plan_text: str | None = None,
) -> dict:
    """정제 스펙/PLAN 존재 시 비자명성·연관성 점검(권고, 비블로킹). 없으면 skip.

    - `plan_text` 가 주어지면(원격 HTTP) 그 본문을 그대로 검사한다.
    - `plan_text` 없이 `project_dir` 도 없으면(원격 HTTP, git/.ralph 미접근) skip.
    - `plan_text` 없이 `project_dir` 만 있으면 <project_dir>/.ralph 에서 산출물을 읽는다.
    """
    if not is_enabled("FLOWOPS_GOVERNANCE_TRACE"):
        return {"status": "skip", "detail": "FLOWOPS_GOVERNANCE_TRACE=off"}

    detail_source: str | None = None
    if plan_text is not None:
        content = plan_text
        detail_source = "plan_text"
    else:
        if project_dir is None:
            # 원격 HTTP 등 git/.ralph 미접근 → 비블로킹 skip
            return {"status": "skip", "detail": "project_dir 없음 → skip"}

        candidates = []
        if issue_key:
            candidates.append(os.path.join(project_dir, ".ralph", "refined", f"{issue_key}.md"))
        candidates.append(os.path.join(project_dir, ".ralph", "PLAN.md"))

        plan_path = next((p for p in candidates if os.path.isfile(p)), None)
        if not plan_path:
            # CI 체크아웃 등 산출물 부재 → 미러에서 자동 skip
            return {"status": "skip", "detail": "PLAN/refined 산출물 없음 → skip"}

        try:
            with open(plan_path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as e:
            return {"status": "skip", "detail": f"plan 읽기 실패: {e}"}
        detail_source = os.path.relpath(plan_path, project_dir)

    if len(content.strip()) < 80:
        loc = detail_source or "plan_text"
        return {"status": "warn", "detail": f"plan 내용 빈약({len(content.strip())}자): {loc}"}

    # 변경된 최상위 영역이 plan에 한 번도 언급되지 않으면 경고(연관성 약함)
    top_dirs = {f.split("/", 1)[0] for f in files if "/" in f}
    unref = [d for d in top_dirs if d and d not in content]
    if top_dirs and len(unref) == len(top_dirs):
        return {
            "status": "warn",
            "detail": f"plan이 변경 영역({', '.join(sorted(top_dirs))})을 언급하지 않음",
        }
    return {"status": "pass", "detail": f"plan 추적 확인: {detail_source}"}


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
def evaluate(
    base: str,
    head: str,
    files: list[str] | None = None,
    *,
    project_dir: str | None = None,
    plan_text: str | None = None,
) -> dict:
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

    # git 해석용 기준 경로(파이프라인·CI 는 루트 실행 → cwd 와 동일). plan-trace 에는
    # project_dir 를 있는 그대로(None 유지) 넘겨 원격 HTTP 에서 skip 되도록 한다.
    pdir = project_dir if project_dir is not None else os.getcwd()

    if files is None:
        files = get_changed_files(base, head, project_dir=pdir)

    checks = {
        "contract_drift": check_contract_drift(files),
        "ticket_ref": check_ticket_ref(issue_key),
        "plan_trace": check_plan_trace(
            issue_key, files, project_dir=project_dir, plan_text=plan_text
        ),
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
