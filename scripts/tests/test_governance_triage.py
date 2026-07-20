"""거버넌스 트리아지(항목 G, 3단 주의-라우터) 단위 테스트.

핵심 불변식:
  - 기본 off(is_opt_in) → triage 키 미추가 + 오늘의 ON dict 와 동일(회귀 0).
  - report-only(TRIAGE=on, ENFORCE=off) → 관측 키만 추가, 코어 서브셋 불변.
  - enforce(ENFORCE=on) → review→pr, block→verdict=fail+merge=block. 강등만.

Usage:
    cd ClickEye && pytest scripts/tests/test_governance_triage.py -v
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_SCRIPTS_DIR)
for _p in (_SCRIPTS_DIR, _REPO_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from governance import core as g  # noqa: E402

_CORE_KEYS = ("merge_decision", "tier", "verdict", "failures")
_TRIAGE_KEYS = ("triage", "risk_score", "triage_reasons", "budget")


@pytest.fixture(autouse=True)
def _clear_toggles(monkeypatch):
    """모든 FLOWOPS_GOVERNANCE* 토글 제거 → 마스터 on / 트리아지 off 에서 시작."""
    for k in list(os.environ):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            monkeypatch.delenv(k, raising=False)
    yield


# ── is_opt_in divergence (is_enabled 와 반대) ──
def test_is_opt_in_default_off():
    # 미설정 → False (is_enabled 는 True 였음 — 반대여야 회귀 0)
    assert g.is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE") is False
    assert g.is_enabled("FLOWOPS_GOVERNANCE_TRIAGE") is True


@pytest.mark.parametrize("val,expected", [
    ("on", True), ("1", True), ("true", True), ("yes", True), ("ON", True),
    ("off", False), ("0", False), ("false", False), ("", False), ("maybe", False),
])
def test_is_opt_in_values(monkeypatch, val, expected):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", val)
    assert g.is_opt_in("FLOWOPS_GOVERNANCE_TRIAGE") is expected


# ── 회귀 가드: triage off → 오늘의 ON dict 와 동일, triage 키 없음 ──
def test_triage_off_no_keys_and_identical():
    files = ["clickeye-web/src/app/page.tsx", "clickeye-api/app/services/x.py"]
    base = g.evaluate("main", "ralph/CE-100", files=files)
    for k in _TRIAGE_KEYS:
        assert k not in base, f"triage off 인데 {k} 유입됨(회귀!)"
    # 오늘의 ON dict 키 집합(고정)
    assert set(base.keys()) == {
        "governance", "issue_key", "tier", "risk_reasons", "checks",
        "failures", "warnings", "verdict", "merge_decision", "changed_files",
    }


def test_master_off_never_adds_triage(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "false")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")  # 켜도 마스터 off 가 우선 단락
    r = g.evaluate("main", "ralph/CE-1", files=["clickeye-contracts/x.ts"], usage={"cost": 999})
    assert r["governance"] == "off"
    for k in _TRIAGE_KEYS:
        assert k not in r


# ── report-only: 관측 키 추가, 코어 서브셋 불변 ──
def test_report_only_adds_keys_core_unchanged(monkeypatch):
    files = ["clickeye-web/src/app/page.tsx"]
    base = g.evaluate("main", "ralph/CE-100", files=files)
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    rep = g.evaluate("main", "ralph/CE-100", files=files)
    for k in _TRIAGE_KEYS:
        assert k in rep
    assert {k: rep[k] for k in _CORE_KEYS} == {k: base[k] for k in _CORE_KEYS}


def test_report_only_high_tier_core_unchanged(monkeypatch):
    # HIGH tier(demote pr) 에서도 report-only 는 코어 불변, triage 만 관측
    files = [
        "clickeye-contracts/protocol/commands.ts",
        "clickeye-contracts/generated/typescript/types.gen.ts",
    ]
    base = g.evaluate("main", "ralph/CE-3", files=files)
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    rep = g.evaluate("main", "ralph/CE-3", files=files)
    assert {k: rep[k] for k in _CORE_KEYS} == {k: base[k] for k in _CORE_KEYS}
    assert rep["merge_decision"] == "pr"  # 기존 RISK_DEMOTE 유래, triage 아님
    assert rep["triage"] == "review"  # risk_score 0.45 >= 0.4


# ── compute_risk_score 밴드 임계 ──
def test_risk_score_files_and_high():
    s0, _ = g.compute_risk_score([], "LOW")
    assert s0 == 0.0
    s_hi, reasons = g.compute_risk_score(["a.py"], "HIGH")
    assert s_hi == round(min(1 / 40.0, 0.30) + 0.40, 3)
    assert any("tier=HIGH" in r for r in reasons)


def test_risk_score_metrics_optional():
    # metrics 없으면 무패널티
    s_none, _ = g.compute_risk_score(["a.py"], "LOW", None)
    # 낮은 커버리지 + 큰 diff → 패널티 가산
    s_pen, reasons = g.compute_risk_score(
        ["a.py"], "LOW", {"coverage": 0.5, "diff_lines": 900}
    )
    assert s_pen > s_none
    assert any("coverage" in r for r in reasons)
    assert any("diff_lines" in r for r in reasons)


def test_risk_score_capped_at_one():
    s, _ = g.compute_risk_score(["f"] * 1000, "HIGH", {"coverage": 0.0, "diff_lines": 99999})
    assert s == 1.0


# ── triage_band 임계/축 ──
def test_triage_band_score_thresholds():
    skip = {"status": "skip", "reasons": []}
    assert g.triage_band(0.1, skip, skip)[0] == "auto"
    assert g.triage_band(0.5, skip, skip)[0] == "review"
    assert g.triage_band(0.9, skip, skip)[0] == "block"


def test_triage_band_env_thresholds(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW", "0.1")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_SCORE_BLOCK", "0.2")
    skip = {"status": "skip", "reasons": []}
    assert g.triage_band(0.15, skip, skip)[0] == "review"
    assert g.triage_band(0.25, skip, skip)[0] == "block"


def test_triage_band_budget_axis():
    skip = {"status": "skip", "reasons": []}
    assert g.triage_band(0.0, {"status": "block", "reasons": []}, skip)[0] == "block"
    assert g.triage_band(0.0, {"status": "review", "reasons": []}, skip)[0] == "review"
    assert g.triage_band(0.0, {"status": "ok", "reasons": []}, skip)[0] == "auto"


# ── assess_budget 주입 밴드 ──
def test_assess_budget_skip_when_no_usage():
    assert g.assess_budget(None)["status"] == "skip"
    assert g.assess_budget({})["status"] == "skip"


def test_assess_budget_cost_limit_block(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT", "10")
    assert g.assess_budget({"cost": 20.0})["status"] == "block"
    assert g.assess_budget({"cost": 5.0})["status"] == "ok"


def test_assess_budget_token_warn(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_TOKEN_WARN", "1000")
    assert g.assess_budget({"tokens": 2000})["status"] == "review"


def test_assess_budget_cost_none_skips_cost_axis(monkeypatch):
    # 구독시트(비용 NULL) → cost 축 미판정, tokens 만
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT", "10")
    r = g.assess_budget({"cost": None, "tokens": 5})
    assert r["status"] == "ok"


# ── assess_rate 전방 훅(기본 skip) ──
def test_assess_rate_skip_without_counters():
    assert g.assess_rate({"cost": 1.0, "tokens": 100})["status"] == "skip"
    assert g.assess_rate(None)["status"] == "skip"


def test_assess_rate_with_counter(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_RATE_RPM_LIMIT", "100")
    assert g.assess_rate({"rpm": 200})["status"] == "block"
    assert g.assess_rate({"rpm": 50})["status"] == "ok"


# ── enforce 강등 매핑 ──
def test_enforce_review_demotes_direct_to_pr(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_WARN", "5")
    r = g.evaluate(
        "main", "ralph/CE-100",
        files=["clickeye-web/src/app/page.tsx"],
        usage={"cost": 6.0, "tokens": 1},
    )
    assert r["triage"] == "review"
    assert r["merge_decision"] == "pr"
    assert r["verdict"] == "pass"


def test_enforce_block_sets_fail(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT", "10")
    r = g.evaluate(
        "main", "ralph/CE-100",
        files=["clickeye-web/src/app/page.tsx"],
        usage={"cost": 20.0, "tokens": 1},
    )
    assert r["triage"] == "block"
    assert r["verdict"] == "fail"
    assert r["merge_decision"] == "block"
    # enforce-block 강등 시 소비자가 사유를 볼 수 있도록 failures 1건 합성.
    assert any(f.startswith("triage_block:") for f in r["failures"]), r["failures"]


def test_report_only_does_not_enforce(monkeypatch):
    # ENFORCE off → band=block 이어도 코어 불변(순수 관측). failures 도 불변([]).
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT", "10")
    files = ["clickeye-web/src/app/page.tsx"]
    r = g.evaluate("main", "ralph/CE-100", files=files, usage={"cost": 20.0})
    assert r["triage"] == "block"
    assert r["verdict"] == "pass" and r["merge_decision"] == "direct"
    assert r["failures"] == []  # report-only 는 failures 합성 안 함


def test_enforce_never_loosens_block(monkeypatch):
    # 계약 드리프트로 이미 block 인 경우, triage review 여도 완화 금지
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_WARN", "5")
    r = g.evaluate(
        "main", "ralph/CE-5",
        files=["clickeye-api/app/api/v1/auth.py"],  # drift → block
        usage={"cost": 6.0},  # triage review
    )
    assert r["verdict"] == "fail" and r["merge_decision"] == "block"


# ── CLI: enforce block → exit 2 ──
def test_cli_enforce_block_exit2(monkeypatch):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            env.pop(k)
    env["FLOWOPS_GOVERNANCE_TRIAGE"] = "on"
    env["FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE"] = "on"
    env["FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT"] = "10"
    r = subprocess.run(
        [
            sys.executable,
            os.path.join(_SCRIPTS_DIR, "pre_merge_gate.py"),
            "--head", "ralph/CE-10",
            "--diff-files", "clickeye-web/src/app/page.tsx",
            "--usage-json", '{"cost": 20.0, "tokens": 1}',
            "--json",
        ],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 2, f"stdout={r.stdout} stderr={r.stderr}"
    import json as _json
    out = _json.loads(r.stdout)
    assert out["triage"] == "block" and out["verdict"] == "fail"
