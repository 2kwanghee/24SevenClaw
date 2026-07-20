"""거버넌스 트리아지(항목 G) FastAPI 접점 테스트.

- 스키마 optional 필드(project_id/usage/metrics, triage 관측 키) 수용.
- 서비스: 원장 집계 → usage 구성 → 커널 트리아지 예산 축 주입 → 강등 매핑.
- DB-less/비-opt-in 하위호환(usage=None → 예산 skip, 코어 불변).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.models.llm_usage_ledger import LlmKeySource, LlmProvider
from app.schemas.governance import (
    GovernanceEvaluateRequest,
    GovernanceEvaluateResponse,
)
from app.services.governance_gate_service import GovernanceGateService
from app.services.llm_ledger_service import LlmLedgerService


@pytest.fixture(autouse=True)
def _clear_toggles(monkeypatch):
    import os

    for k in list(os.environ):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            monkeypatch.delenv(k, raising=False)
    yield


# ── 스키마 optional 필드 ──
def test_request_accepts_triage_fields():
    pid = uuid.uuid4()
    req = GovernanceEvaluateRequest(
        head="ralph/CE-1",
        project_id=pid,
        usage={"cost": 1.0, "tokens": 10},
        metrics={"coverage": 0.5},
    )
    assert req.project_id == pid
    assert req.usage == {"cost": 1.0, "tokens": 10}


def test_request_defaults_backward_compatible():
    req = GovernanceEvaluateRequest(head="ralph/CE-1")
    assert req.project_id is None and req.usage is None and req.metrics is None


def test_response_accepts_triage_keys():
    resp = GovernanceEvaluateResponse(
        governance="on",
        verdict="pass",
        tier="LOW",
        merge_decision="direct",
        triage="review",
        risk_score=0.45,
        triage_reasons=["x"],
        budget={"status": "review", "reasons": ["y"]},
    )
    assert resp.triage == "review" and resp.risk_score == 0.45


# ── 서비스: DB-less/비-opt-in 하위호환 ──
@pytest.mark.asyncio
async def test_service_db_less_no_triage():
    # db 미주입 + 트리아지 off → 오늘 동작 그대로(triage 키 없음)
    req = GovernanceEvaluateRequest(head="ralph/CE-2", files=["clickeye-web/src/app/page.tsx"])
    result = await GovernanceGateService().evaluate(req)
    assert "triage" not in result
    assert result["merge_decision"] == "direct" and result["verdict"] == "pass"


@pytest.mark.asyncio
async def test_service_project_id_ignored_without_budget_optin(db_session, monkeypatch):
    # 트리아지 on 이지만 예산 opt-in 없음 → 원장 조회 skip, usage=None → budget skip
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    pid = uuid.uuid4()
    await _seed_org_cost(db_session, pid, Decimal("100.0"))
    req = GovernanceEvaluateRequest(
        head="ralph/CE-2", files=["clickeye-web/src/app/page.tsx"], project_id=pid
    )
    result = await GovernanceGateService(db_session).evaluate(req)
    assert result["triage"] == "auto"  # 예산 미반영
    assert result["budget"]["status"] == "skip"


# ── 서비스: 원장 → usage → 예산 강등 ──
@pytest.mark.asyncio
async def test_service_ledger_budget_block_enforced(db_session, monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT", "10")
    pid = uuid.uuid4()
    await _seed_org_cost(db_session, pid, Decimal("50.0"))  # > limit 10 → block

    req = GovernanceEvaluateRequest(
        head="ralph/CE-2", files=["clickeye-web/src/app/page.tsx"], project_id=pid
    )
    result = await GovernanceGateService(db_session).evaluate(req)
    assert result["triage"] == "block"
    assert result["verdict"] == "fail" and result["merge_decision"] == "block"


@pytest.mark.asyncio
async def test_service_subscription_cost_null_skips_cost_axis(db_session, monkeypatch):
    # 구독시트 행만(비용 NULL) → 비용 축 자연 skip(정당). 토큰만 집계.
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT", "10")
    pid = uuid.uuid4()
    svc = LlmLedgerService(db_session)
    await svc.record(
        provider=LlmProvider.anthropic,
        key_source=LlmKeySource.subscription_seat,
        model="claude-opus-4-8",
        request_kind="wizard_preview",
        input_tokens=100,
        output_tokens=50,
        cost=None,
        project_id=pid,
    )
    req = GovernanceEvaluateRequest(
        head="ralph/CE-2", files=["clickeye-web/src/app/page.tsx"], project_id=pid
    )
    result = await GovernanceGateService(db_session).evaluate(req)
    # 비용 한도 초과 없음(cost=None) → 예산 ok, triage auto
    assert result["budget"]["status"] == "ok"
    assert result["triage"] == "auto"


# ── M1: HTTP 응답에 triage null 키가 새지 않음(계약 정합) ──
_TRIAGE_KEYS = ("triage", "risk_score", "triage_reasons", "budget")


@pytest.mark.asyncio
async def test_http_triage_off_omits_keys(client):
    # 트리아지 off(기본) → 응답 JSON 에 triage 관측 키가 아예 없어야 함(null 주입 금지).
    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": "ralph/CE-2", "files": ["clickeye-web/src/app/page.tsx"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for k in _TRIAGE_KEYS:
        assert k not in body, f"triage off 인데 응답에 {k} 유입: {body.get(k)!r}"
    assert body["merge_decision"] == "direct" and body["verdict"] == "pass"


@pytest.mark.asyncio
async def test_http_triage_on_includes_keys(client, monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": "ralph/CE-2", "files": ["clickeye-web/src/app/page.tsx"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for k in _TRIAGE_KEYS:
        assert k in body, f"triage on 인데 응답에 {k} 없음"
    assert body["triage"] == "auto"


async def _seed_org_cost(db_session, project_id, cost: Decimal) -> None:
    svc = LlmLedgerService(db_session)
    await svc.record(
        provider=LlmProvider.anthropic,
        key_source=LlmKeySource.org_api_key,
        model="claude-opus-4-8",
        request_kind="modernize_summary",
        input_tokens=100,
        output_tokens=50,
        cost=cost,
        project_id=project_id,
    )
