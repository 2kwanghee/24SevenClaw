"""preflight 서비스 단위 테스트 — 체크리스트 생성 / 렌더링 / 승인 판정.

DB / HTTP 의존 X. 순수 함수 단위 검증.
"""

from __future__ import annotations

from app.services.modernize.preflight import (
    build_preflight_checklist,
    evaluate_approval,
    render_markdown,
)

_SAFE_REC = {
    "title": "Django 3.2 → 5.0",
    "category": "upgrade",
    "target_path": "requirements.txt",
    "before": {"pkg": "django", "version": "3.2"},
    "after": {"pkg": "django", "version": "5.0", "breaking_changes": []},
    "risk": "med",
    "rationale_md": "EOL 대응",
    "prompt_md": "# Upgrade\n\nAcceptance: ...",
}
_FS = {"test_file_ratio": 0.3}


def test_all_pass_when_no_issues() -> None:
    content = build_preflight_checklist(recommendations=[_SAFE_REC], framework_signals=_FS)
    assert content["overall_verdict"] == "pass"
    assert all(item["verdict"] == "pass" for item in content["checklist"])
    assert content["acknowledged_high_risk"] is False


def test_breaking_changes_detected_as_warn() -> None:
    rec = {
        **_SAFE_REC,
        "after": {"pkg": "django", "version": "5.0", "breaking_changes": ["ORM API 변경"]},
    }
    content = build_preflight_checklist(recommendations=[rec], framework_signals=_FS)
    item = next(i for i in content["checklist"] if i["key"] == "breaking_changes")
    assert item["verdict"] == "warn"
    assert "ORM API 변경" in item["detail_md"]
    assert content["overall_verdict"] == "warn"


def test_db_migration_without_rollback_notes_blocks() -> None:
    rec = {
        **_SAFE_REC,
        "category": "migrate",
        "title": "PostgreSQL 12 → 16 마이그레이션",
        "rationale_md": "메이저 버전 업그레이드",
        "prompt_md": "스키마 변경 적용",
    }
    content = build_preflight_checklist(recommendations=[rec], framework_signals=_FS)
    item = next(i for i in content["checklist"] if i["key"] == "rollback_strategy")
    assert item["verdict"] == "block"
    assert content["overall_verdict"] == "block"


def test_db_migration_with_rollback_notes_passes() -> None:
    rec = {
        **_SAFE_REC,
        "category": "migrate",
        "title": "PostgreSQL 12 → 16 마이그레이션",
        "rationale_md": "백업 후 리허설 환경에서 마이그레이션 검증, 실패 시 롤백 스크립트로 복원",
    }
    content = build_preflight_checklist(recommendations=[rec], framework_signals=_FS)
    item = next(i for i in content["checklist"] if i["key"] == "rollback_strategy")
    assert item["verdict"] == "pass"


def test_low_test_file_ratio_warns() -> None:
    content = build_preflight_checklist(
        recommendations=[_SAFE_REC], framework_signals={"test_file_ratio": 0.01}
    )
    item = next(i for i in content["checklist"] if i["key"] == "test_coverage")
    assert item["verdict"] == "warn"


def test_missing_test_file_ratio_warns() -> None:
    content = build_preflight_checklist(recommendations=[_SAFE_REC], framework_signals={})
    item = next(i for i in content["checklist"] if i["key"] == "test_coverage")
    assert item["verdict"] == "warn"
    assert "감지하지 못했습니다" in item["detail_md"]


def test_high_risk_task_blocks_and_requires_ack() -> None:
    rec = {**_SAFE_REC, "risk": "high", "target_path": "app/auth/login.py"}
    content = build_preflight_checklist(recommendations=[rec], framework_signals=_FS)
    item = next(i for i in content["checklist"] if i["key"] == "high_risk_tasks")
    assert item["verdict"] == "block"
    assert item["requires_manual_ack"] is True
    assert content["overall_verdict"] == "block"


def test_evaluate_approval_blocks_without_ack_for_high_risk() -> None:
    rec = {**_SAFE_REC, "risk": "high"}
    content = build_preflight_checklist(recommendations=[rec], framework_signals=_FS)
    can_approve, reason = evaluate_approval(content, ack_high_risk=False)
    assert can_approve is False
    assert reason is not None


def test_evaluate_approval_passes_with_ack_for_high_risk_only() -> None:
    rec = {**_SAFE_REC, "risk": "high"}
    content = build_preflight_checklist(recommendations=[rec], framework_signals=_FS)
    can_approve, reason = evaluate_approval(content, ack_high_risk=True)
    assert can_approve is True
    assert reason is None


def test_evaluate_approval_still_blocks_non_ackable_block_even_with_ack() -> None:
    """rollback_strategy block 은 requires_manual_ack=False → ack_high_risk 로 우회 불가."""
    rec = {
        **_SAFE_REC,
        "category": "migrate",
        "title": "DB 마이그레이션",
        "rationale_md": "",
        "prompt_md": "",
    }
    content = build_preflight_checklist(recommendations=[rec], framework_signals=_FS)
    can_approve, reason = evaluate_approval(content, ack_high_risk=True)
    assert can_approve is False
    assert reason is not None


def test_render_markdown_includes_all_sections() -> None:
    content = build_preflight_checklist(recommendations=[_SAFE_REC], framework_signals=_FS)
    md = render_markdown(content)
    assert "# Pre-flight Review" in md
    assert "Breaking Change 목록" in md
    assert "롤백 전략" in md
    assert "테스트 커버리지" in md
    assert "HIGH 리스크 작업" in md
