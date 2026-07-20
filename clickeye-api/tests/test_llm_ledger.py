"""LLM 원장 admin 엔드포인트 + 집계 테스트 (CE-299)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.llm_usage_ledger import (
    LlmKeySource,
    LlmProvider,
    LlmUsageLedger,
)
from app.models.user import User
from app.services.llm_ledger_service import LlmLedgerService


async def _seed(db_session, project_id) -> None:
    svc = LlmLedgerService(db_session)
    await svc.record(
        provider=LlmProvider.anthropic,
        key_source=LlmKeySource.org_api_key,
        model="claude-opus-4-8",
        request_kind="modernize_summary",
        input_tokens=100,
        output_tokens=50,
        cost=Decimal("0.001750"),
        project_id=project_id,
    )
    await svc.record(
        provider=LlmProvider.anthropic,
        key_source=LlmKeySource.subscription_seat,
        model="claude-opus-4-8",
        request_kind="wizard_preview",
        input_tokens=200,
        output_tokens=80,
        cost=None,
        project_id=project_id,
    )


@pytest.mark.asyncio
async def test_summary_aggregates_by_key_source(db_session) -> None:
    project_id = uuid.uuid4()
    await _seed(db_session, project_id)

    svc = LlmLedgerService(db_session)
    summary = await svc.summary_by_project(project_id)

    assert summary.total_input_tokens == 300
    assert summary.total_output_tokens == 130
    assert summary.total_cost == Decimal("0.001750")
    key_sources = {b.key_source: b for b in summary.by_key_source}
    assert key_sources["org_api_key"].cost == Decimal("0.001750")
    assert key_sources["subscription_seat"].cost is None


@pytest.mark.asyncio
async def test_list_requires_admin(client: AsyncClient, auth_headers: dict) -> None:
    # auth_headers 는 일반 member(권한 부족) → 403
    resp = await client.get("/api/v1/llm-ledger", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_allows_admin(client: AsyncClient, db_session, admin_auth_headers: dict) -> None:
    rows = (await db_session.execute(select(LlmUsageLedger))).scalars().all()
    assert isinstance(rows, list)  # 테이블 생성 확인
    resp = await client.get("/api/v1/llm-ledger", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "total" in body


@pytest.fixture
async def admin_auth_headers(db_session) -> dict:
    """settings:manage 권한을 가진 admin 유저 토큰."""
    from app.core.security import create_access_token

    admin = User(
        id=uuid.uuid4(),
        email=f"admin-{uuid.uuid4().hex[:8]}@test.io",
        password_hash="x",
        display_name="관리자",
        is_active=True,
        system_role="admin",
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token({"sub": str(admin.id)})
    return {"Authorization": f"Bearer {token}"}
