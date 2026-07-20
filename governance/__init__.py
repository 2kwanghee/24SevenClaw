"""clickeye-governance — 머지 직전 거버넌스 게이트 커널(stdlib 전용 SSOT).

순수 로직은 `governance.core` 에 있다. 여기서는 공개 API 를 재노출한다.
"""

from __future__ import annotations

from governance.core import (
    CONTRACT_SURFACE_PREFIXES,
    CONTRACTS_PREFIX,
    GENERATED_CLIENT_PREFIX,
    HIGH_PATH_PATTERNS,
    HIGH_PREFIXES,
    ISSUE_KEY_RE,
    OPENAPI_SPEC,
    TRIAGE_SCORE_BLOCK_DEFAULT,
    TRIAGE_SCORE_REVIEW_DEFAULT,
    assess_budget,
    assess_rate,
    check_contract_drift,
    check_plan_trace,
    check_ticket_ref,
    classify_risk,
    compute_risk_score,
    evaluate,
    extract_issue_key,
    get_changed_files,
    is_enabled,
    is_opt_in,
    triage_band,
)

__all__ = [
    "evaluate",
    "check_contract_drift",
    "check_ticket_ref",
    "check_plan_trace",
    "classify_risk",
    "extract_issue_key",
    "is_enabled",
    "is_opt_in",
    "get_changed_files",
    "compute_risk_score",
    "assess_budget",
    "assess_rate",
    "triage_band",
    "CONTRACT_SURFACE_PREFIXES",
    "CONTRACTS_PREFIX",
    "GENERATED_CLIENT_PREFIX",
    "HIGH_PATH_PATTERNS",
    "HIGH_PREFIXES",
    "ISSUE_KEY_RE",
    "OPENAPI_SPEC",
    "TRIAGE_SCORE_REVIEW_DEFAULT",
    "TRIAGE_SCORE_BLOCK_DEFAULT",
]
