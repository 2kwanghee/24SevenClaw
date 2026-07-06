"""Phase 5 — 작업 전 사전검토(Pre-flight) 게이트.

Plan Gate / Governance Gate(HIGH 리스크 강등)와 동일한 철학을 modernize 실행(Phase 6)
직전에 적용한다. 선택된 권장안(recommendations)과 as-is 스캔 결과를 근거로 체크리스트를
생성하고, 항목별 pass/warn/block 을 판정한다. block 항목이 남아 있으면 승인이 불가능하며
(HIGH 리스크 작업은 예외적으로 수동 확인(ack) 시 승인 가능), 승인 전에는 실행 팩(ZIP)
발급도 차단된다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

# 마이그레이션/DB 전환 여부를 텍스트에서 추정하기 위한 키워드
_DB_MIGRATION_KEYWORDS = ("database", "db ", "postgres", "mysql", "mariadb", "sqlite", "migration")
_ROLLBACK_KEYWORDS = ("rollback", "롤백", "backup", "백업", "리허설", "rehearsal")
# HIGH 리스크로 간주할 경로/제목 키워드 (auth/보안/데이터 이관)
_HIGH_RISK_KEYWORDS = (
    "auth",
    "secur",
    "credential",
    "secret",
    "password",
    "token",
    "payment",
    "migration",
    "migrate",
)

_ITEM_TITLES: dict[str, str] = {
    "breaking_changes": "Breaking Change 목록",
    "rollback_strategy": "롤백 전략",
    "test_coverage": "테스트 커버리지",
    "high_risk_tasks": "HIGH 리스크 작업",
}


def _item(
    *, key: str, verdict: str, detail_md: str, requires_manual_ack: bool = False
) -> dict[str, Any]:
    return {
        "key": key,
        "title": _ITEM_TITLES[key],
        "verdict": verdict,
        "detail_md": detail_md,
        "requires_manual_ack": requires_manual_ack,
    }


def _looks_like_db_migration(rec: dict[str, Any]) -> bool:
    if str(rec.get("category") or "") == "migrate":
        return True
    before = rec.get("before") or {}
    after = rec.get("after") or {}
    if isinstance(before, dict) and before.get("db_type"):
        return True
    if isinstance(after, dict) and after.get("db_type"):
        return True
    text = " ".join(
        [str(rec.get("target_path") or ""), str(rec.get("title") or "")]
    ).lower()
    return any(kw in text for kw in _DB_MIGRATION_KEYWORDS)


def _has_rollback_notes(rec: dict[str, Any]) -> bool:
    text = " ".join([str(rec.get("rationale_md") or ""), str(rec.get("prompt_md") or "")]).lower()
    return any(kw in text for kw in _ROLLBACK_KEYWORDS)


def _is_high_risk(rec: dict[str, Any]) -> bool:
    if str(rec.get("risk") or "") == "high":
        return True
    text = " ".join([str(rec.get("target_path") or ""), str(rec.get("title") or "")]).lower()
    return any(kw in text for kw in _HIGH_RISK_KEYWORDS)


def _check_breaking_changes(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    changes: list[str] = []
    for rec in recommendations:
        after = rec.get("after") or {}
        if not isinstance(after, dict):
            continue
        for change in after.get("breaking_changes") or []:
            changes.append(f"{rec.get('title', '(제목 없음)')}: {change}")

    if not changes:
        return _item(
            key="breaking_changes",
            verdict="pass",
            detail_md="선택된 권장안에서 감지된 breaking change 가 없습니다.",
        )
    lines = "\n".join(f"- {c}" for c in changes)
    return _item(
        key="breaking_changes",
        verdict="warn",
        detail_md=(
            f"breaking change {len(changes)}건이 감지되었습니다. "
            f"각 항목의 마이그레이션 노트를 확인하세요.\n\n{lines}"
        ),
    )


def _check_rollback_strategy(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    migrations = [r for r in recommendations if _looks_like_db_migration(r)]
    if not migrations:
        return _item(
            key="rollback_strategy",
            verdict="pass",
            detail_md="DB 마이그레이션을 수반하는 작업이 없습니다.",
        )
    missing = [r for r in migrations if not _has_rollback_notes(r)]
    if missing:
        lines = "\n".join(f"- {r.get('title', '(제목 없음)')}" for r in missing)
        return _item(
            key="rollback_strategy",
            verdict="block",
            detail_md=(
                f"DB 마이그레이션 작업 {len(missing)}건에 롤백 전략(백업·리허설·롤백 스크립트) "
                f"언급이 없습니다. rationale/prompt 에 롤백 계획을 보강하세요.\n\n{lines}"
            ),
        )
    return _item(
        key="rollback_strategy",
        verdict="pass",
        detail_md=f"DB 마이그레이션 작업 {len(migrations)}건 모두 롤백 전략이 확인되었습니다.",
    )


def _check_test_coverage(framework_signals: dict[str, Any]) -> dict[str, Any]:
    ratio = framework_signals.get("test_file_ratio") if framework_signals else None
    if ratio is None:
        return _item(
            key="test_coverage",
            verdict="warn",
            detail_md="테스트 파일 비율을 감지하지 못했습니다 (as-is 스캔 데이터 없음).",
        )
    pct = round(float(ratio) * 100, 1)
    if ratio < 0.05:
        return _item(
            key="test_coverage",
            verdict="warn",
            detail_md=(
                f"테스트 파일 비율이 {pct}% 로 낮습니다. "
                "회귀 위험에 유의하고 수동 검증을 계획하세요."
            ),
        )
    return _item(
        key="test_coverage",
        verdict="pass",
        detail_md=f"테스트 파일 비율 {pct}%.",
    )


def _check_high_risk_tasks(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    high = [r for r in recommendations if _is_high_risk(r)]
    if not high:
        return _item(
            key="high_risk_tasks",
            verdict="pass",
            detail_md="HIGH 리스크로 분류된 작업이 없습니다.",
        )
    lines = "\n".join(
        f"- {r.get('title', '(제목 없음)')} (risk={r.get('risk', 'n/a')})" for r in high
    )
    return _item(
        key="high_risk_tasks",
        verdict="block",
        detail_md=(
            f"auth/보안/데이터 이관 관련 HIGH 리스크 작업 {len(high)}건이 있습니다. "
            f"내용을 확인한 뒤 승인 시 수동 확인(ack_high_risk)이 필요합니다.\n\n{lines}"
        ),
        requires_manual_ack=True,
    )


def _overall_verdict(items: list[dict[str, Any]]) -> str:
    verdicts = {i["verdict"] for i in items}
    if "block" in verdicts:
        return "block"
    if "warn" in verdicts:
        return "warn"
    return "pass"


def build_preflight_checklist(
    *,
    recommendations: list[dict[str, Any]],
    framework_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """선택된 권장안 + as-is 스캔 신호로 Pre-flight 체크리스트를 생성한다."""
    items = [
        _check_breaking_changes(recommendations),
        _check_rollback_strategy(recommendations),
        _check_test_coverage(framework_signals or {}),
        _check_high_risk_tasks(recommendations),
    ]
    return {
        "checklist": items,
        "overall_verdict": _overall_verdict(items),
        "acknowledged_high_risk": False,
        "generated_at": datetime.now(UTC).isoformat(),
    }


_VERDICT_LABEL = {"pass": "✅ PASS", "warn": "⚠️ WARN", "block": "⛔ BLOCK"}


def render_markdown(content: dict[str, Any]) -> str:
    """`preflight-review.md` 산출물 렌더링."""
    overall = content.get("overall_verdict", "")
    lines = [
        "# Pre-flight Review",
        "",
        f"**종합 판정**: {_VERDICT_LABEL.get(overall, overall)}",
        "",
    ]
    for item in content.get("checklist", []):
        label = _VERDICT_LABEL.get(item["verdict"], item["verdict"])
        lines.append(f"## {item['title']} — {label}")
        lines.append("")
        lines.append(item["detail_md"])
        lines.append("")
    if content.get("acknowledged_high_risk"):
        lines.append("_HIGH 리스크 작업에 대한 수동 확인(ack)이 완료된 상태로 승인되었습니다._")
    return "\n".join(lines)


def evaluate_approval(
    content: dict[str, Any], *, ack_high_risk: bool
) -> tuple[bool, str | None]:
    """승인 가능 여부 판정.

    block 항목 중 `requires_manual_ack=True` (HIGH 리스크) 는 ack_high_risk=True 시 예외
    적으로 통과된다. 그 외 block 항목이 하나라도 남아 있으면 승인 불가.
    """
    blocking = [
        i
        for i in content.get("checklist", [])
        if i["verdict"] == "block" and not (i.get("requires_manual_ack") and ack_high_risk)
    ]
    if blocking:
        titles = ", ".join(i["title"] for i in blocking)
        return False, f"다음 항목이 BLOCK 상태라 승인할 수 없습니다: {titles}"
    return True, None
