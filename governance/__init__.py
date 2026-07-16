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
    check_contract_drift,
    check_plan_trace,
    check_ticket_ref,
    classify_risk,
    evaluate,
    extract_issue_key,
    get_changed_files,
    is_enabled,
)

__all__ = [
    "evaluate",
    "check_contract_drift",
    "check_ticket_ref",
    "check_plan_trace",
    "classify_risk",
    "extract_issue_key",
    "is_enabled",
    "get_changed_files",
    "CONTRACT_SURFACE_PREFIXES",
    "CONTRACTS_PREFIX",
    "GENERATED_CLIENT_PREFIX",
    "HIGH_PATH_PATTERNS",
    "HIGH_PREFIXES",
    "ISSUE_KEY_RE",
    "OPENAPI_SPEC",
]
