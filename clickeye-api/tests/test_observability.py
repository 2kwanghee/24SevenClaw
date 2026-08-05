"""관측 화면(관측 C) 집계 API 테스트 (CE-388).

전부 GET/읽기 전용이라 SQLite in-memory(client/db_session fixture)로 충분하다.
`PipelineRunService.ingest()` 는 PostgreSQL 전용 upsert 를 쓰므로 seed 는
`PipelineRunEvent` ORM 을 직접 add 한다.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.delivery_event import DeliveryEvent
from app.models.intake import IntakeRequest, IntakeServiceKey
from app.models.llm_usage_ledger import LlmKeySource, LlmProvider, LlmUsageLedger
from app.models.pipeline_run_event import PipelineRunEvent
from app.models.project import Project
from app.models.user import User

_BASE = "/api/v1/observability"


@pytest.fixture
async def admin_auth_headers(db_session: AsyncSession) -> dict:
    """settings:manage 권한을 가진 admin 유저 토큰."""
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


async def _seed_project(db_session: AsyncSession, *, status: str = "active") -> Project:
    owner = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4().hex[:8]}@test.io",
        password_hash="x",
        display_name="오너",
        is_active=True,
    )
    db_session.add(owner)
    await db_session.flush()
    project = Project(
        id=uuid.uuid4(),
        owner_id=owner.id,
        name="테스트 프로젝트",
        slug=f"proj-{uuid.uuid4().hex[:8]}",
        status=status,
    )
    db_session.add(project)
    await db_session.commit()
    return project


async def _seed_intake(db_session: AsyncSession) -> IntakeRequest:
    service_key = IntakeServiceKey(
        id=uuid.uuid4(),
        name="테스트 서비스 키",
        key_hash=f"hash-{uuid.uuid4().hex}",
        is_active=True,
    )
    db_session.add(service_key)
    await db_session.flush()
    intake = IntakeRequest(
        id=uuid.uuid4(),
        service_key_id=service_key.id,
        input_type="structured",
        title="테스트 인테이크",
        payload={},
    )
    db_session.add(intake)
    await db_session.commit()
    return intake


# ─────────────────────────────────────────────────────────────────────────────
# summary
# ─────────────────────────────────────────────────────────────────────────────


async def test_summary_empty_returns_zero_counts(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/summary", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["projects_by_status"] == {}
    assert body["intake_by_status"] == {}
    assert body["pipeline_run_success_count"] == 0
    assert body["pipeline_run_failure_count"] == 0
    assert body["recent_delivery_events"] == []


async def test_summary_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/summary")
    assert resp.status_code in (401, 403)


async def test_summary_with_data_aggregates(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    p1 = await _seed_project(db_session, status="active")
    await _seed_project(db_session, status="archived")
    intake = await _seed_intake(db_session)

    db_session.add(
        PipelineRunEvent(
            id=uuid.uuid4(),
            run_id="RUN-1",
            issue_key="CE-1",
            event="run_done",
            data={"outcome": "merged"},
        )
    )
    db_session.add(
        DeliveryEvent(
            id=uuid.uuid4(),
            intake_id=intake.id,
            project_id=p1.id,
            event_type="accepted",
            actor_type="human",
            detail="수락됨",
        )
    )
    await db_session.commit()

    resp = await client.get(f"{_BASE}/summary", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["projects_by_status"] == {"active": 1, "archived": 1}
    assert body["intake_by_status"] == {"pending_review": 1}
    assert body["pipeline_run_success_count"] == 1
    assert len(body["recent_delivery_events"]) == 1
    assert body["recent_delivery_events"][0]["event_type"] == "accepted"


# ─────────────────────────────────────────────────────────────────────────────
# usage
# ─────────────────────────────────────────────────────────────────────────────


async def test_usage_empty_returns_empty_buckets(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/usage", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["buckets"] == []
    assert body["total_request_count"] == 0


async def test_usage_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/usage")
    assert resp.status_code in (401, 403)


async def test_usage_invalid_group_by_returns_422(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(
        f"{_BASE}/usage", params={"group_by": "invalid_value"}, headers=admin_auth_headers
    )
    assert resp.status_code == 422


async def test_usage_with_data_sums_by_model(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    for _ in range(2):
        db_session.add(
            LlmUsageLedger(
                id=uuid.uuid4(),
                provider=LlmProvider.anthropic,
                key_source=LlmKeySource.subscription_seat,
                model="claude-opus-4-8",
                request_kind="wizard_preview",
                input_tokens=100,
                output_tokens=50,
            )
        )
    await db_session.commit()

    resp = await client.get(f"{_BASE}/usage", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["group_by"] == "model"
    assert len(body["buckets"]) == 1
    assert body["buckets"][0]["key"] == "claude-opus-4-8"
    assert body["buckets"][0]["input_tokens"] == 200
    assert body["buckets"][0]["output_tokens"] == 100
    assert body["total_request_count"] == 2


# ─────────────────────────────────────────────────────────────────────────────
# runs
# ─────────────────────────────────────────────────────────────────────────────


async def test_runs_empty_returns_empty_list(client: AsyncClient, admin_auth_headers: dict) -> None:
    resp = await client.get(f"{_BASE}/runs", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


async def test_runs_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/runs")
    assert resp.status_code in (401, 403)


async def test_runs_invalid_limit_returns_422(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/runs", params={"limit": 0}, headers=admin_auth_headers)
    assert resp.status_code == 422


async def test_runs_with_data_flags_model_mismatch(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    now = datetime.now(UTC)
    db_session.add(
        PipelineRunEvent(
            id=uuid.uuid4(),
            run_id="RUN-42",
            issue_key="CE-42",
            event="run_done",
            data={"outcome": "merged"},
            occurred_at=now,
        )
    )
    db_session.add(
        PipelineRunEvent(
            id=uuid.uuid4(),
            run_id="RUN-42",
            issue_key="CE-42",
            event="model_mismatch",
            data={},
            occurred_at=now,
        )
    )
    await db_session.commit()

    resp = await client.get(f"{_BASE}/runs", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["model_mismatch"] is True


# ─────────────────────────────────────────────────────────────────────────────
# runs/{issue_key}
# ─────────────────────────────────────────────────────────────────────────────


async def test_run_thread_unknown_issue_key_returns_empty(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/runs/CE-NOPE", headers=admin_auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ─────────────────────────────────────────────────────────────────────────────
# seats
# ─────────────────────────────────────────────────────────────────────────────


async def test_seats_empty_returns_empty_list(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/seats", headers=admin_auth_headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_seats_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/seats")
    assert resp.status_code in (401, 403)
