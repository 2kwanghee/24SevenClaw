"""거버넌스 정책 조회 API(GET /governance/policy) 테스트.

- 인증 사용자 200 + 필드 구조 정합(gate_rules/high_risk/toggles/risk_demote/source_note).
- 미인증 401.
- 토글 env 변경이 응답에 반영(마스터 off, _CONTRACT off 등 monkeypatch).

정책 로직은 커널(governance.core.policy_summary)이 SSOT 이므로 라우터/서비스는 위임만 한다.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def _clear_toggles(monkeypatch):
    """테스트 격리: FLOWOPS_GOVERNANCE* 환경변수를 초기화(기본 상태로)."""
    for k in list(os.environ):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            monkeypatch.delenv(k, raising=False)
    yield


# ── (a) 인증 사용자 200 + 필드 구조 ──
@pytest.mark.asyncio
async def test_policy_authenticated_ok(client, auth_headers):
    resp = await client.get("/api/v1/governance/policy", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # 최상위 필드 구조.
    assert set(body.keys()) == {
        "governance_enabled",
        "gate_rules",
        "high_risk",
        "toggles",
        "risk_demote_to_pr",
        "source_note",
    }
    assert isinstance(body["governance_enabled"], bool)
    assert isinstance(body["source_note"], str) and body["source_note"]

    # gate_rules: 블로킹 2 + 권고 1, 각 룰 구조 정합.
    rules = {r["key"]: r for r in body["gate_rules"]}
    assert set(rules) == {"contract_drift", "ticket_ref", "plan_trace"}
    assert rules["contract_drift"]["mode"] == "block"
    assert rules["ticket_ref"]["mode"] == "block"
    assert rules["plan_trace"]["mode"] == "warn"
    for r in body["gate_rules"]:
        assert set(r.keys()) == {"key", "label", "mode", "enabled"}
        assert isinstance(r["enabled"], bool) and isinstance(r["label"], str)

    # high_risk: 커널 상수 노출.
    assert body["high_risk"]["prefixes"] == ["clickeye-contracts/", "clickeye-infra/"]
    assert body["high_risk"]["patterns"]  # 정규식 문자열 목록(비어있지 않음)

    # toggles: 마스터 포함, 값은 전부 bool.
    assert "FLOWOPS_GOVERNANCE" in body["toggles"]
    assert all(isinstance(v, bool) for v in body["toggles"].values())

    # 기본(미설정) 상태 = 마스터 on, 기존 게이트 on, 트리아지 off.
    assert body["governance_enabled"] is True
    assert body["toggles"]["FLOWOPS_GOVERNANCE_CONTRACT"] is True
    assert body["toggles"]["FLOWOPS_GOVERNANCE_TRIAGE"] is False
    assert body["risk_demote_to_pr"] is True


# ── (b) 미인증 ──
@pytest.mark.asyncio
async def test_policy_unauthenticated_rejected(client):
    # 유효하지 않은 토큰 → 401(우리 코드 경로: decode 실패).
    resp = await client.get(
        "/api/v1/governance/policy",
        headers={"Authorization": "Bearer invalid.token.value"},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_policy_no_auth_header_rejected(client):
    # 인증 헤더 자체 부재 → 접근 차단(HTTPBearer auto_error: 401/403).
    resp = await client.get("/api/v1/governance/policy")
    assert resp.status_code in (401, 403), resp.text


# ── (c) 토글 env 변경 반영 ──
@pytest.mark.asyncio
async def test_policy_reflects_master_off(client, auth_headers, monkeypatch):
    # W2: 마스터 off → evaluate() 가 모든 룰을 무력화하므로 정책도 정합해야 한다.
    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "off")
    resp = await client.get("/api/v1/governance/policy", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["governance_enabled"] is False
    assert body["toggles"]["FLOWOPS_GOVERNANCE"] is False
    # 개별 토글이 기본 on 이어도 유효 enabled 는 마스터 AND 개별 → 전부 False.
    assert all(r["enabled"] is False for r in body["gate_rules"]), body["gate_rules"]
    assert body["risk_demote_to_pr"] is False


@pytest.mark.asyncio
async def test_policy_reflects_contract_toggle_off(client, auth_headers, monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "off")
    resp = await client.get("/api/v1/governance/policy", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["toggles"]["FLOWOPS_GOVERNANCE_CONTRACT"] is False
    rules = {r["key"]: r for r in body["gate_rules"]}
    assert rules["contract_drift"]["enabled"] is False
    # 다른 룰은 영향 없음(기본 on).
    assert rules["ticket_ref"]["enabled"] is True


@pytest.mark.asyncio
async def test_policy_reflects_triage_opt_in(client, auth_headers, monkeypatch):
    # 트리아지는 is_opt_in(기본 off) — 명시 opt-in 시에만 True.
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    resp = await client.get("/api/v1/governance/policy", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["toggles"]["FLOWOPS_GOVERNANCE_TRIAGE"] is True


# ── W3: 최상위 키셋 ↔ 스키마 필드 동치(드리프트 무음 방지) ──
@pytest.mark.no_db
def test_policy_summary_keyset_matches_schema():
    """policy_summary() 최상위 키셋이 GovernancePolicyResponse.model_fields 와 동치.

    스키마가 extra 를 무시하면 커널이 새 최상위 키를 추가해도 조용히 탈락한다. 이 테스트로
    드리프트를 명시적으로 잡는다. (파생 룰은 gate_rules 리스트 항목이지 최상위 키가 아님 →
    triage_enforce 가 켜져도 최상위 키셋은 불변.)
    """
    from governance.core import policy_summary

    from app.schemas.governance import GovernancePolicyResponse

    assert set(policy_summary().keys()) == set(GovernancePolicyResponse.model_fields)


@pytest.mark.no_db
def test_policy_summary_keyset_stable_when_triage_enforce_on(monkeypatch):
    # 파생 룰이 조건부로 늘어도 최상위 키셋은 불변임을 명시 검증.
    from governance.core import policy_summary

    from app.schemas.governance import GovernancePolicyResponse

    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE", "on")
    assert set(policy_summary().keys()) == set(GovernancePolicyResponse.model_fields)


# ── W1: 트리아지 집행축 파생 룰(evaluate 실조건과 정확 일치) ──
@pytest.mark.no_db
def test_triage_enforce_rule_absent_by_default():
    from governance.core import policy_summary

    keys = {r["key"] for r in policy_summary()["gate_rules"]}
    assert keys == {"contract_drift", "ticket_ref", "plan_trace"}
    assert "triage_enforce" not in keys


@pytest.mark.no_db
def test_triage_enforce_rule_requires_both_optins(monkeypatch):
    from governance.core import policy_summary

    # _TRIAGE 만 opt-in(집행 없음) → 파생 룰 미포함(band 계산만, direct/pr 강등 안 함).
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    keys = {r["key"] for r in policy_summary()["gate_rules"]}
    assert "triage_enforce" not in keys


@pytest.mark.no_db
def test_triage_enforce_rule_present_when_enforced(monkeypatch):
    from governance.core import policy_summary

    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE", "on")
    rules = {r["key"]: r for r in policy_summary()["gate_rules"]}
    assert "triage_enforce" in rules
    assert rules["triage_enforce"]["mode"] == "block"
    assert rules["triage_enforce"]["enabled"] is True


@pytest.mark.no_db
def test_triage_enforce_rule_suppressed_when_master_off(monkeypatch):
    # 마스터 off 면 evaluate() 가 단락 → 집행축도 발생 안 함 → 파생 룰 미포함.
    from governance.core import policy_summary

    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "off")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE", "on")
    keys = {r["key"] for r in policy_summary()["gate_rules"]}
    assert "triage_enforce" not in keys
