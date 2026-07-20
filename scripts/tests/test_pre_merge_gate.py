"""pre_merge_gate (거버넌스 SSOT) 단위 테스트.

검증기·위험분류·종합판정·토글 회귀를 git 없이(diff-files 주입) 검증한다.

Usage:
    cd ClickEye && pytest scripts/tests/test_pre_merge_gate.py -v
"""

from __future__ import annotations

import os
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# 커널은 저장소 루트의 governance 패키지에 단일 존재(SSOT). cwd 무관하게 import 되도록
# 저장소 루트(=scripts 의 상위)를 sys.path 에 추가한다.
_REPO_ROOT = os.path.dirname(_SCRIPTS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from governance import core as g  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_toggles(monkeypatch):
    """모든 FLOWOPS_GOVERNANCE* 토글 제거 → 기본 on 상태에서 시작."""
    for k in list(os.environ):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            monkeypatch.delenv(k, raising=False)
    yield


# ── extract_issue_key ──
def test_extract_issue_key_from_branch():
    assert g.extract_issue_key("ralph/CE-123") == "CE-123"
    assert g.extract_issue_key("ralph/24S-7") == "24S-7"


def test_extract_issue_key_descriptive_branch_finds_key():
    # 서술형 브랜치명에 키 병기 → 어디서든 탐색해 추출
    assert g.extract_issue_key("feature/web/CE-302-delivery-console") == "CE-302"
    assert g.extract_issue_key("fix/api/24S-142-something") == "24S-142"
    assert g.extract_issue_key("chore/governance/CE-302-branch-ticket-ref") == "CE-302"


def test_extract_issue_key_slash_without_key_returns_last_segment():
    # 슬래시는 있으나 키 없음 → 마지막 세그먼트 반환(check_ticket_ref에서 형식 불량 차단)
    key = g.extract_issue_key("feature/web/no-ticket-here")
    assert key == "no-ticket-here"
    assert g.check_ticket_ref(key)["status"] == "fail"


def test_extract_issue_key_no_slash_returns_none():
    assert g.extract_issue_key("main") is None


def test_check_ticket_ref_pass_on_descriptive_branch():
    key = g.extract_issue_key("feature/web/CE-302-delivery-console")
    assert g.check_ticket_ref(key)["status"] == "pass"


# ── contract-drift ──
def test_contract_drift_surface_without_spec_fails():
    r = g.check_contract_drift(["clickeye-api/app/api/v1/auth.py"])
    assert r["status"] == "fail"


def test_contract_drift_surface_with_spec_passes():
    r = g.check_contract_drift(
        ["clickeye-api/app/api/v1/auth.py", "clickeye-contracts/openapi/openapi.json"]
    )
    assert r["status"] == "pass"


def test_contract_drift_contracts_without_generated_fails():
    r = g.check_contract_drift(["clickeye-contracts/protocol/commands.ts"])
    assert r["status"] == "fail"


def test_contract_drift_contracts_with_generated_passes():
    r = g.check_contract_drift(
        [
            "clickeye-contracts/protocol/commands.ts",
            "clickeye-contracts/generated/typescript/types.gen.ts",
        ]
    )
    assert r["status"] == "pass"


def test_contract_drift_non_surface_passes():
    r = g.check_contract_drift(["clickeye-api/app/services/auth_service.py"])
    assert r["status"] == "pass"  # services 는 계약면 아님 → 오탐 없음


def test_contract_drift_toggle_off_skips(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "false")
    r = g.check_contract_drift(["clickeye-api/app/api/v1/auth.py"])
    assert r["status"] == "skip"


# ── ticket-ref ──
def test_ticket_ref_valid_passes():
    assert g.check_ticket_ref("CE-123")["status"] == "pass"


def test_ticket_ref_missing_skips():
    assert g.check_ticket_ref(None)["status"] == "skip"


def test_ticket_ref_malformed_fails():
    assert g.check_ticket_ref("not_a_key")["status"] == "fail"


def test_ticket_ref_24s_prefix_valid():
    # 24S- 는 [A-Z0-9]+ 로 정상 통과(과거 [A-Z]+ 버그 회귀 방지)
    assert g.check_ticket_ref("24S-42")["status"] == "pass"


# ── plan-trace ──
def test_plan_trace_no_artifacts_skips():
    # .ralph/refined/<key>.md, PLAN.md 부재(보통 테스트 환경) → skip
    r = g.check_plan_trace("CE-999999", ["clickeye-api/app/services/x.py"])
    assert r["status"] in ("skip", "warn", "pass")  # 블로킹 아님 보장
    assert r["status"] != "fail"


def test_plan_trace_with_artifact(tmp_path):
    # 임시 project_dir 에 .ralph/refined/<key>.md 를 만들어 pass/warn 경로 커버
    refined = tmp_path / ".ralph" / "refined"
    refined.mkdir(parents=True)
    (refined / "CE-77.md").write_text(
        "# 구현 스펙\nclickeye-api 의 서비스 로직을 충분히 길게 설명한 정제 스펙 본문입니다." * 2,
        encoding="utf-8",
    )
    r = g.check_plan_trace(
        "CE-77", ["clickeye-api/app/services/x.py"], project_dir=str(tmp_path)
    )
    assert r["status"] == "pass"

    # plan이 변경 영역을 전혀 언급 안 하면 warn
    (refined / "CE-78.md").write_text("관련 없는 내용을 길게 적은 정제 스펙 본문." * 4, encoding="utf-8")
    r2 = g.check_plan_trace(
        "CE-78", ["clickeye-web/src/app/page.tsx"], project_dir=str(tmp_path)
    )
    assert r2["status"] == "warn"


# ── CLI(main) ──
def test_cli_json_pass_exit0():
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            os.path.join(_SCRIPTS_DIR, "pre_merge_gate.py"),
            "--head", "ralph/CE-9",
            "--diff-files", "clickeye-web/src/app/page.tsx",
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    import json as _json

    out = _json.loads(r.stdout)
    assert out["verdict"] == "pass" and out["tier"] == "LOW"


def test_cli_contract_drift_exit2():
    import subprocess

    r = subprocess.run(
        [
            sys.executable,
            os.path.join(_SCRIPTS_DIR, "pre_merge_gate.py"),
            "--head", "ralph/CE-10",
            "--diff-files", "clickeye-api/app/api/v1/auth.py",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2  # 블로킹


# ── classify_risk ──
@pytest.mark.parametrize(
    "path",
    [
        "clickeye-contracts/protocol/commands.ts",
        "clickeye-infra/docker/docker-compose.yml",
        "clickeye-api/app/api/v1/auth.py",
        "clickeye-api/app/core/security.py",
    ],
)
def test_classify_risk_high(path):
    assert g.classify_risk([path])["tier"] == "HIGH"


def test_classify_risk_low():
    assert g.classify_risk(["clickeye-web/src/app/page.tsx"])["tier"] == "LOW"


# ── evaluate 종합 ──
def test_evaluate_master_off_bypasses(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "false")
    r = g.evaluate("main", "ralph/CE-1", files=["clickeye-contracts/x.ts"])
    assert r["governance"] == "off"
    assert r["verdict"] == "pass" and r["merge_decision"] == "direct" and r["tier"] == "LOW"


def test_evaluate_low_tier_direct():
    r = g.evaluate(
        "main", "ralph/CE-2", files=["clickeye-web/src/app/page.tsx"]
    )
    assert r["verdict"] == "pass" and r["merge_decision"] == "direct" and r["tier"] == "LOW"


def test_evaluate_high_tier_demotes_to_pr():
    # contracts 변경 + generated 동반(드리프트 통과) → HIGH 강등만 발생
    r = g.evaluate(
        "main",
        "ralph/CE-3",
        files=[
            "clickeye-contracts/protocol/commands.ts",
            "clickeye-contracts/generated/typescript/types.gen.ts",
        ],
    )
    assert r["verdict"] == "pass"
    assert r["tier"] == "HIGH"
    assert r["merge_decision"] == "pr"


def test_evaluate_high_tier_demote_off_stays_direct(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_RISK_DEMOTE", "false")
    r = g.evaluate(
        "main",
        "ralph/CE-4",
        files=[
            "clickeye-contracts/protocol/commands.ts",
            "clickeye-contracts/generated/typescript/types.gen.ts",
        ],
    )
    assert r["tier"] == "HIGH" and r["merge_decision"] == "direct"


def test_evaluate_contract_drift_blocks():
    r = g.evaluate("main", "ralph/CE-5", files=["clickeye-api/app/api/v1/auth.py"])
    assert r["verdict"] == "fail" and r["merge_decision"] == "block"
    assert any("contract_drift" in f for f in r["failures"])


def test_evaluate_bad_ticket_blocks():
    r = g.evaluate("main", "garbage-branch", files=["clickeye-web/src/app/page.tsx"])
    # garbage-branch 는 슬래시 없음 → 키 None → ticket skip, 차단 아님
    assert r["verdict"] == "pass"
    # 슬래시 있고 형태 불량이면 차단
    r2 = g.evaluate("main", "ralph/bad_key", files=["clickeye-web/src/app/page.tsx"])
    assert r2["verdict"] == "fail" and any("ticket_ref" in f for f in r2["failures"])
