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


# ⚠️ is_opt_in 은 is_enabled 와 **의도적으로 반대(divergence)** 다.
#   is_enabled  → 미설정/빈값 = True  (기존 게이트 항목은 기본 on)
#   is_opt_in   → 미설정/그 외 = False, 명시적 opt-in 값만 True (신규 트리아지는 기본 off)
# 트리아지 토글에는 반드시 is_opt_in 을 써야 회귀 0(기본 off)이 보장된다. 실수로
# is_enabled 를 쓰면 기본 on 이 되어 오늘의 ON dict 를 오염(신규 키 유입)시킨다.
_TRUTHY = {"1", "true", "on", "yes"}


def is_opt_in(key: str) -> bool:
    """명시적 opt-in 값(1/true/on/yes, 소문자)만 True. 미설정/그 외는 False."""
    return os.environ.get(key, "").strip().lower() in _TRUTHY


def _env_float(key: str, default: float) -> float:
    """FLOWOPS_GOVERNANCE_* float 임계값 읽기. 미설정/파싱불가면 default(결정적)."""
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


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
# 브랜치 문자열 어디서든 Linear 이슈 키를 탐색(대문자/숫자 세그먼트-숫자).
# lowercase 세그먼트(web/api 등)는 매치하지 않고, 24S-142 처럼 숫자로 시작하는 키도 매치.
ISSUE_KEY_SEARCH_RE = re.compile(r"[A-Z0-9]+-\d+")


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
    """브랜치에서 Linear 이슈 키(대문자/숫자-숫자)를 탐색.

    ralph/CE-123·feature/web/CE-302-desc → CE-302. 슬래시 없으면 None(skip).
    슬래시는 있으나 키가 없으면 마지막 세그먼트를 반환(형식 불량으로 차단됨).
    """
    if "/" not in head:
        return None
    m = ISSUE_KEY_SEARCH_RE.search(head)
    if m:
        return m.group(0)
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


# ── 트리아지(3단 주의-라우터) ────────────────────────────────────────────────
# 항목 G(P2). 순수·결정적(시각/네트워크 없음). 기본 off(is_opt_in)이며 report-only 는
# 코어 서브셋 {merge_decision,tier,verdict,failures} 를 절대 바꾸지 않는다(순수 관측).
# 임계 env 는 전부 FLOWOPS_GOVERNANCE_ 접두 → 테스트 픽스처가 자동 클리어(회귀 격리).
TRIAGE_SCORE_REVIEW_DEFAULT = 0.40  # risk_score 이 값 이상 → review 밴드
TRIAGE_SCORE_BLOCK_DEFAULT = 0.80   # risk_score 이 값 이상 → block 밴드
# risk_score 구성 가중치(포화·결정적). 표면 최소화를 위해 env 노출 없이 상수 고정.
_RISK_FILE_SCALE = 40.0      # 변경 파일 수 정규화 분모
_RISK_FILE_CAP = 0.30        # 파일 수 기여 상한
_RISK_HIGH_WEIGHT = 0.40     # tier=HIGH 기여
_RISK_COVERAGE_FLOOR = 0.70  # 커버리지 이 미만이면 패널티
_RISK_COVERAGE_PENALTY = 0.20
_RISK_DIFF_LINES_THRESHOLD = 400
_RISK_DIFF_LINES_PENALTY = 0.20

_STATUS_ORDER = {"skip": 0, "ok": 1, "review": 2, "block": 3}
_BAND_ORDER = {"auto": 0, "review": 1, "block": 2}


def _is_num(x: object) -> bool:
    """실수/정수만 True(bool 제외). JSON 주입값의 안전한 수치 판정."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _worse_status(a: str, b: str) -> str:
    return a if _STATUS_ORDER.get(a, 0) >= _STATUS_ORDER.get(b, 0) else b


def _worse_band(a: str, b: str) -> str:
    return a if _BAND_ORDER.get(a, 0) >= _BAND_ORDER.get(b, 0) else b


def compute_risk_score(
    files: list[str],
    tier: str,
    metrics: dict | None = None,
) -> tuple[float, list[str]]:
    """주의(위험) 점수 [0,1] 산출. 순수·결정적.

    축: 변경 파일 수(포화) + tier=HIGH 가산. metrics(coverage/diff_lines)는 optional
    주입이며 없으면 무패널티(하위호환). 부동소수 오차 방지 위해 round(3).
    """
    reasons: list[str] = []
    score = 0.0
    n = len(files or [])
    if n:
        contrib = min(n / _RISK_FILE_SCALE, _RISK_FILE_CAP)
        score += contrib
        reasons.append(f"changed_files={n} (+{round(contrib, 3)})")
    if tier == "HIGH":
        score += _RISK_HIGH_WEIGHT
        reasons.append(f"tier=HIGH (+{_RISK_HIGH_WEIGHT})")
    if metrics:
        cov = metrics.get("coverage")
        if _is_num(cov) and cov < _RISK_COVERAGE_FLOOR:
            score += _RISK_COVERAGE_PENALTY
            reasons.append(f"coverage={cov}<{_RISK_COVERAGE_FLOOR} (+{_RISK_COVERAGE_PENALTY})")
        dl = metrics.get("diff_lines")
        if _is_num(dl) and dl > _RISK_DIFF_LINES_THRESHOLD:
            score += _RISK_DIFF_LINES_PENALTY
            reasons.append(
                f"diff_lines={dl}>{_RISK_DIFF_LINES_THRESHOLD} (+{_RISK_DIFF_LINES_PENALTY})"
            )
    return round(min(score, 1.0), 3), reasons


def assess_budget(usage: dict | None) -> dict:
    """예산(누적 토큰/비용) 상태. usage 없으면 skip(비블로킹).

    usage 계약(FastAPI 가 원장 요약을 float 로 정규화해 주입):
      {"cost": float|None, "tokens": int}
    한도/경고 임계는 env(FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_*). <=0(미설정)이면 해당 축 비활성.
    """
    if not usage:
        return {"status": "skip", "reasons": ["usage 없음 → 예산 skip(비블로킹)"]}

    reasons: list[str] = []
    status = "ok"
    cost = usage.get("cost")
    tokens = usage.get("tokens")

    cost_limit = _env_float("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT", 0.0)
    cost_warn = _env_float("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_WARN", 0.0)
    token_limit = _env_float("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_TOKEN_LIMIT", 0.0)
    token_warn = _env_float("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_TOKEN_WARN", 0.0)

    if _is_num(cost):
        if cost_limit > 0 and cost >= cost_limit:
            status = _worse_status(status, "block")
            reasons.append(f"cost={cost}>=limit {cost_limit}")
        elif cost_warn > 0 and cost >= cost_warn:
            status = _worse_status(status, "review")
            reasons.append(f"cost={cost}>=warn {cost_warn}")
    if _is_num(tokens):
        if token_limit > 0 and tokens >= token_limit:
            status = _worse_status(status, "block")
            reasons.append(f"tokens={tokens}>=limit {token_limit}")
        elif token_warn > 0 and tokens >= token_warn:
            status = _worse_status(status, "review")
            reasons.append(f"tokens={tokens}>=warn {token_warn}")

    if not reasons:
        reasons.append("예산 여유(임계 미설정/미도달)")
    return {"status": status, "reasons": reasons}


def assess_rate(usage: dict | None) -> dict:
    """레이트(TPM/RPM) 상태 — **전방 훅(forward hook)**.

    원장에 윈도우 카운터가 없어(실측은 CE-297 대기) usage 에 rpm/tpm 키가 없으면
    skip(비블로킹)한다. 카운터가 주입되면 임계로 판정. 현재 파이프라인/로컬은 항상 skip.
    TODO(CE-297): 슬라이딩 윈도우 카운터가 생기면 usage 에 rpm/tpm 을 주입.
    """
    if not usage:
        return {"status": "skip", "reasons": ["usage 없음 → 레이트 skip"]}
    rpm = usage.get("rpm")
    tpm = usage.get("tpm")
    if rpm is None and tpm is None:
        return {
            "status": "skip",
            "reasons": ["레이트 윈도우 카운터 부재(CE-297 대기) → skip(전방 훅)"],
        }
    reasons: list[str] = []
    status = "ok"
    rpm_limit = _env_float("FLOWOPS_GOVERNANCE_TRIAGE_RATE_RPM_LIMIT", 0.0)
    tpm_limit = _env_float("FLOWOPS_GOVERNANCE_TRIAGE_RATE_TPM_LIMIT", 0.0)
    if _is_num(rpm) and rpm_limit > 0 and rpm >= rpm_limit:
        status = _worse_status(status, "block")
        reasons.append(f"rpm={rpm}>=limit {rpm_limit}")
    if _is_num(tpm) and tpm_limit > 0 and tpm >= tpm_limit:
        status = _worse_status(status, "block")
        reasons.append(f"tpm={tpm}>=limit {tpm_limit}")
    if not reasons:
        reasons.append("레이트 여유")
    return {"status": status, "reasons": reasons}


def triage_band(score: float, budget: dict, rate: dict) -> tuple[str, list[str]]:
    """3단 밴드 결정: auto|review|block. 축 = risk_score + budget + rate.

    밴드 강도 auto<review<block. 어느 축이든 block 이면 block, review 면 최소 review.
    """
    reasons: list[str] = []
    review_th = _env_float(
        "FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW", TRIAGE_SCORE_REVIEW_DEFAULT
    )
    block_th = _env_float(
        "FLOWOPS_GOVERNANCE_TRIAGE_SCORE_BLOCK", TRIAGE_SCORE_BLOCK_DEFAULT
    )

    band = "auto"
    if score >= block_th:
        band = _worse_band(band, "block")
        reasons.append(f"risk_score {score}>=block {block_th}")
    elif score >= review_th:
        band = _worse_band(band, "review")
        reasons.append(f"risk_score {score}>=review {review_th}")

    for axis, res in (("budget", budget), ("rate", rate)):
        st = res.get("status")
        if st == "block":
            band = _worse_band(band, "block")
            reasons.append(f"{axis}=block")
        elif st == "review":
            band = _worse_band(band, "review")
            reasons.append(f"{axis}=review")
    return band, reasons


# ── 종합 ───────────────────────────────────────────────────────────────────
def evaluate(
    base: str,
    head: str,
    files: list[str] | None = None,
    *,
    project_dir: str | None = None,
    plan_text: str | None = None,
    usage: dict | None = None,
    metrics: dict | None = None,
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

    result = {
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

    # ── 트리아지 오버레이(항목 G, opt-in) ────────────────────────────────────
    # 기본 off(is_opt_in). off 면 위 base result 를 그대로 반환 → 오늘의 ON dict 와
    # 바이트 동일(신규 키 0). 마스터 off 는 위에서 이미 단락되어 여기 도달하지 않는다.
    if is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE"):
        score, score_reasons = compute_risk_score(files, tier, metrics)
        budget = assess_budget(usage)
        rate = assess_rate(usage)
        band, band_reasons = triage_band(score, budget, rate)
        # 관측 키 추가(코어 서브셋은 report-only 에서 불변 — 순수 관측).
        result["triage"] = band
        result["risk_score"] = score
        result["budget"] = budget
        result["triage_reasons"] = score_reasons + band_reasons + rate["reasons"]
        # 집행(강등)은 별도 opt-in 일 때만. 강등만(승격/새 값 없음).
        # report-only(비enforce)는 failures 포함 코어 서브셋 불변 — 아래 블록에 도달 안 함.
        if is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE"):
            if band == "block":
                result["verdict"] = "fail"
                result["merge_decision"] = "block"
                # 소비자(파이프라인)가 차단 사유를 볼 수 있도록 failures 에 1건 합성 추가.
                summary = "; ".join(band_reasons) or band
                result["failures"] = result["failures"] + [f"triage_block: {summary}"]
            elif band == "review" and result["merge_decision"] == "direct":
                result["merge_decision"] = "pr"

    return result


# ── 정책 요약(읽기 전용 노출) ────────────────────────────────────────────────
def policy_summary() -> dict:
    """전역 머지-게이트 정책을 직렬화 가능한 dict 로 요약한다(순수·additive).

    evaluate() 와 로직을 공유하지 않고 커널 상수/토글 함수만 읽어 노출한다. HTTP
    어댑터(FastAPI `GET /governance/policy`)가 이 값을 그대로 스키마로 감싸 반환하므로
    정책의 이중관리가 발생하지 않는다. stdlib 전용이며 어떤 기존 로직도 변경하지 않는다.

    토글 상태는 **이 함수가 실행되는 프로세스의 환경변수 기준**이다(API 서버 env). 따라서
    파이프라인/CI 프로세스의 실제 적용값과 다를 수 있으며 source_note 로 이를 명시한다.
    블로킹 룰(contract-drift/ticket-ref)과 권고 룰(plan-trace)의 mode·enabled, 고위험
    경로(prefixes/patterns), 위험강등(risk-demote) 여부를 함께 노출한다.

    evaluate() 실효값 정합: 마스터(FLOWOPS_GOVERNANCE) off 면 evaluate() 가 즉시 단락하여
    모든 룰이 무력화되므로, gate_rules[].enabled 와 risk_demote_to_pr 는 마스터 AND 개별
    토글로 계산한다("마스터 off인데 enabled=true" 모순 방지). 최상위 governance_enabled 는
    마스터 플래그 자체를 그대로 노출한다. 트리아지 집행축(triage_enforce)은 evaluate() 의
    실제 조건(마스터 on + _TRIAGE + _TRIAGE_ENFORCE 모두 opt-in)일 때만 파생 룰로 포함한다.
    """
    master = is_enabled("FLOWOPS_GOVERNANCE")
    gate_rules = [
        {
            "key": "contract_drift",
            "label": "계약 드리프트",
            "mode": "block",
            "enabled": master and is_enabled("FLOWOPS_GOVERNANCE_CONTRACT"),
        },
        {
            "key": "ticket_ref",
            "label": "티켓 참조",
            "mode": "block",
            "enabled": master and is_enabled("FLOWOPS_GOVERNANCE_TICKET"),
        },
        {
            "key": "plan_trace",
            "label": "플랜 추적성",
            "mode": "warn",
            "enabled": master and is_enabled("FLOWOPS_GOVERNANCE_TRACE"),
        },
    ]
    # 트리아지 집행(band==block→차단, band==review→direct 강등 to pr)은 마스터 on +
    # _TRIAGE + _TRIAGE_ENFORCE 가 모두 opt-in 일 때만 evaluate() 에서 발생한다. 그 조건일
    # 때만 파생 블로킹 룰을 노출한다(거짓 보고 금지 — 비활성 시엔 아예 포함하지 않음).
    triage_enforce_active = (
        master
        and is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE")
        and is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE")
    )
    if triage_enforce_active:
        gate_rules.append(
            {
                "key": "triage_enforce",
                "label": "트리아지 집행",
                "mode": "block",
                "enabled": True,
            }
        )
    toggles = {
        # 마스터 + 기존 게이트 항목(기본 on, is_enabled 로 읽음).
        "FLOWOPS_GOVERNANCE": master,
        "FLOWOPS_GOVERNANCE_CONTRACT": is_enabled("FLOWOPS_GOVERNANCE_CONTRACT"),
        "FLOWOPS_GOVERNANCE_TICKET": is_enabled("FLOWOPS_GOVERNANCE_TICKET"),
        "FLOWOPS_GOVERNANCE_TRACE": is_enabled("FLOWOPS_GOVERNANCE_TRACE"),
        "FLOWOPS_GOVERNANCE_RISK_DEMOTE": is_enabled("FLOWOPS_GOVERNANCE_RISK_DEMOTE"),
        # 트리아지(신규, 기본 off, is_opt_in 로 읽음).
        "FLOWOPS_GOVERNANCE_TRIAGE": is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE"),
        "FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE": is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE"),
        "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET": is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET"),
    }
    return {
        "governance_enabled": master,
        "gate_rules": gate_rules,
        "high_risk": {
            "prefixes": list(HIGH_PREFIXES),
            "patterns": [p.pattern for p in HIGH_PATH_PATTERNS],
        },
        "toggles": toggles,
        "risk_demote_to_pr": master and is_enabled("FLOWOPS_GOVERNANCE_RISK_DEMOTE"),
        "source_note": (
            "토글 상태는 API 서버 env 기준값(파이프라인/CI와 다를 수 있음). "
            "마스터 off 시 모든 룰 무력화. 게이트 룰·고위험 경로 자체는 항상 정확."
        ),
    }
