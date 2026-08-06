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
from app.models.user_anthropic_credentials import UserAnthropicCredentials

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


# ─────────────────────────────────────────────────────────────────────────────
# CE-402 신규 테스트용 헬퍼
# ─────────────────────────────────────────────────────────────────────────────


async def _seed_pipeline_run_event(
    db_session: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    outcome: str,
    created_at: datetime,
) -> PipelineRunEvent:
    event = PipelineRunEvent(
        id=uuid.uuid4(),
        run_id=f"RUN-{uuid.uuid4().hex[:8]}",
        issue_key="CE-402",
        project_id=project_id,
        event="run_done",
        data={"outcome": outcome},
        created_at=created_at,
    )
    db_session.add(event)
    await db_session.commit()
    return event


async def _seed_ledger_row(
    db_session: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    seat_id: uuid.UUID | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost: object = None,
    created_at: datetime | None = None,
    task_id: str | None = None,
) -> LlmUsageLedger:
    row = LlmUsageLedger(
        id=uuid.uuid4(),
        project_id=project_id,
        seat_id=seat_id,
        provider=LlmProvider.anthropic,
        key_source=LlmKeySource.subscription_seat,
        model="claude-opus-4-8",
        request_kind="wizard_preview",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost,
        created_at=created_at if created_at is not None else datetime.now(UTC),
        task_id=task_id,
    )
    db_session.add(row)
    await db_session.commit()
    return row


# ─────────────────────────────────────────────────────────────────────────────
# summary — CE-402 (days/trend_days, daily_outcomes)
# ─────────────────────────────────────────────────────────────────────────────


async def test_summary_with_days_query_returns_200(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/summary", params={"days": 30}, headers=admin_auth_headers)
    assert resp.status_code == 200


async def test_summary_empty_daily_outcomes_fills_trend_day_slots(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/summary", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["daily_outcomes"]) == 3
    for slot in body["daily_outcomes"]:
        assert slot["success"] == 0
        assert slot["failure"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# usage — CE-402 (project_id 필터)
# ─────────────────────────────────────────────────────────────────────────────


async def test_usage_filters_by_project_id(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    p1 = await _seed_project(db_session)
    p2 = await _seed_project(db_session)
    await _seed_ledger_row(db_session, project_id=p1.id, input_tokens=100, output_tokens=10)
    await _seed_ledger_row(db_session, project_id=p2.id, input_tokens=999, output_tokens=999)

    resp = await client.get(
        f"{_BASE}/usage",
        params={"project_id": str(p1.id)},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_input_tokens"] == 100
    assert body["total_output_tokens"] == 10


# ─────────────────────────────────────────────────────────────────────────────
# delivery-board — CE-411
# ─────────────────────────────────────────────────────────────────────────────


async def test_delivery_board_empty_returns_empty_projects(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/delivery-board", headers=admin_auth_headers)
    assert resp.status_code == 200
    assert resp.json()["projects"] == []


async def test_delivery_board_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"{_BASE}/delivery-board")
    assert resp.status_code in (401, 403)


async def test_delivery_board_excludes_intake_without_project(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    await _seed_intake(db_session)  # project_id None — self-repo 성격, 제외 대상

    resp = await client.get(f"{_BASE}/delivery-board", headers=admin_auth_headers)
    assert resp.status_code == 200
    assert resp.json()["projects"] == []


async def test_delivery_board_ticket_without_events_stays_issued(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    project = await _seed_project(db_session)
    intake = await _seed_intake(db_session)
    intake.project_id = project.id
    intake.status = "accepted"
    intake.tickets_status = "issued"
    intake.tickets = [{"key": "T1", "identifier": "CE-500", "issue_id": "abc", "title": "티켓1"}]
    db_session.add(intake)
    await db_session.commit()

    resp = await client.get(f"{_BASE}/delivery-board", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["projects"]) == 1
    proj = body["projects"][0]
    assert proj["project_id"] == str(project.id)
    assert proj["intake_status"] == "accepted"
    assert len(proj["tickets"]) == 1
    ticket = proj["tickets"][0]
    assert ticket["key"] == "CE-500"
    assert ticket["title"] == "티켓1"
    assert ticket["stage"] == "issued"
    assert ticket["active"] is False
    assert ticket["outcome"] is None
    assert ticket["duration_s"] is None


async def test_delivery_board_ticket_progress_derives_stage_and_outcome(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    project = await _seed_project(db_session)
    intake = await _seed_intake(db_session)
    intake.project_id = project.id
    intake.tickets_status = "issued"
    intake.tickets = [{"key": "T1", "identifier": "CE-501", "issue_id": "abc", "title": "티켓2"}]
    db_session.add(intake)
    await db_session.commit()

    now = datetime.now(UTC)
    db_session.add(
        PipelineRunEvent(
            id=uuid.uuid4(),
            run_id="RUN-501",
            issue_key="CE-501",
            project_id=project.id,
            event="refine_done",
            data={},
            created_at=now,
        )
    )
    db_session.add(
        PipelineRunEvent(
            id=uuid.uuid4(),
            run_id="RUN-501",
            issue_key="CE-501",
            project_id=project.id,
            event="run_done",
            data={"outcome": "merged"},
            created_at=now,
        )
    )
    await db_session.commit()

    resp = await client.get(f"{_BASE}/delivery-board", headers=admin_auth_headers)
    assert resp.status_code == 200
    ticket = resp.json()["projects"][0]["tickets"][0]
    assert ticket["stage"] == "done"
    assert ticket["outcome"] == "merged"
    assert len(ticket["stage_history"]) == 2
    assert ticket["stage_history"][0]["stage"] == "refining"
    assert ticket["stage_history"][1]["stage"] == "done"


async def test_delivery_board_stages_use_delivery_events_first_occurrence(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    project = await _seed_project(db_session)
    intake = await _seed_intake(db_session)
    intake.project_id = project.id
    db_session.add(intake)
    await db_session.commit()

    db_session.add(
        DeliveryEvent(
            id=uuid.uuid4(),
            intake_id=intake.id,
            project_id=project.id,
            event_type="refined",
            actor_type="machine",
        )
    )
    db_session.add(
        DeliveryEvent(
            id=uuid.uuid4(),
            intake_id=intake.id,
            project_id=project.id,
            event_type="accepted",
            actor_type="human",
        )
    )
    await db_session.commit()

    resp = await client.get(f"{_BASE}/delivery-board", headers=admin_auth_headers)
    assert resp.status_code == 200
    stages = resp.json()["projects"][0]["stages"]
    assert stages["received_at"] is not None
    assert stages["refined_at"] is not None
    assert stages["accepted_at"] is not None
    assert stages["issued_at"] is None


# ─────────────────────────────────────────────────────────────────────────────
# projects/{project_id}/summary — CE-402
# ─────────────────────────────────────────────────────────────────────────────


async def test_project_summary_aggregates_tokens_and_seats(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    project = await _seed_project(db_session)
    owner = User(
        id=uuid.uuid4(),
        email=f"seat-{uuid.uuid4().hex[:8]}@test.io",
        password_hash="x",
        display_name="시트오너",
        is_active=True,
    )
    db_session.add(owner)
    await db_session.flush()
    seat = UserAnthropicCredentials(
        id=uuid.uuid4(),
        user_id=owner.id,
        credential_type="oauth_token",
        encrypted_api_key="enc",
    )
    db_session.add(seat)
    await db_session.commit()

    await _seed_ledger_row(
        db_session, project_id=project.id, seat_id=seat.id, input_tokens=50, output_tokens=20
    )
    await _seed_ledger_row(
        db_session, project_id=project.id, seat_id=None, input_tokens=30, output_tokens=5
    )

    resp = await client.get(f"{_BASE}/projects/{project.id}/summary", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_input_tokens"] == 80
    assert body["total_output_tokens"] == 25

    seats_by_seat_id = {s["seat_id"]: s for s in body["seats"]}
    assert seats_by_seat_id[str(seat.id)]["input_tokens"] == 50
    assert seats_by_seat_id[str(seat.id)]["account_email"] == owner.email
    assert seats_by_seat_id[None]["input_tokens"] == 30
    assert seats_by_seat_id[None]["account_email"] is None


async def test_project_summary_unknown_project_returns_empty_200(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/projects/{uuid.uuid4()}/summary", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_input_tokens"] == 0
    assert body["seats"] == []
    assert body["first_activity_at"] is None


# ─────────────────────────────────────────────────────────────────────────────
# CE-402 QA 보완 테스트 (리뷰어 지적 전수)
# ─────────────────────────────────────────────────────────────────────────────


# usage — task_id 필터 무회귀 (project_id 파라미터 추가 후에도 기존 동작 유지)
async def test_usage_task_id_filter_unaffected_by_project_id_param(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    project = await _seed_project(db_session)
    await _seed_ledger_row(
        db_session, project_id=project.id, task_id="CE-100", input_tokens=100, output_tokens=10
    )
    await _seed_ledger_row(
        db_session, project_id=project.id, task_id="CE-200", input_tokens=999, output_tokens=999
    )

    resp = await client.get(
        f"{_BASE}/usage", params={"task_id": "CE-100"}, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    # task_id 필터가 project_id 파라미터 추가와 무관하게 여전히 CE-100 만 집계해야 함
    assert body["total_input_tokens"] == 100
    assert body["total_output_tokens"] == 10
    assert body["total_request_count"] == 1


# usage — 비 UUID project_id 처리.
# NOTE(CE-402): 리뷰어는 422 를 기대했으나, 서비스는 잘못된/미존재 project_id 에 대해
# 500 대신 빈 집계(200)를 반환하는 것이 문서화된 관측 라우터 전역 컨벤션이다
# (observability_service.py:56-63, 165-166). 따라서 실제 동작(200 빈 집계)을 검증한다.
async def test_usage_invalid_project_id_returns_empty_200(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    project = await _seed_project(db_session)
    await _seed_ledger_row(db_session, project_id=project.id, input_tokens=100, output_tokens=10)

    resp = await client.get(
        f"{_BASE}/usage", params={"project_id": "not-a-uuid"}, headers=admin_auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["buckets"] == []
    assert body["total_input_tokens"] == 0
    assert body["total_request_count"] == 0


# summary — days 생략 시 응답이 days=7 명시 요청과 동일 (무회귀)
async def test_summary_days_default_matches_explicit_seven(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp_default = await client.get(f"{_BASE}/summary", headers=admin_auth_headers)
    resp_explicit = await client.get(
        f"{_BASE}/summary", params={"days": 7}, headers=admin_auth_headers
    )
    assert resp_default.status_code == 200
    assert resp_explicit.status_code == 200
    assert resp_default.json() == resp_explicit.json()


# summary — days 경계 검증 (Query ge=1, le=90)
async def test_summary_days_out_of_range_returns_422(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp_high = await client.get(
        f"{_BASE}/summary", params={"days": 91}, headers=admin_auth_headers
    )
    resp_low = await client.get(f"{_BASE}/summary", params={"days": 0}, headers=admin_auth_headers)
    assert resp_high.status_code == 422
    assert resp_low.status_code == 422


# summary — trend_days > days 일 때 effective_trend_days = min(trend_days, days) 캡핑
async def test_summary_trend_days_capped_to_days(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(
        f"{_BASE}/summary",
        params={"days": 2, "trend_days": 14},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    # trend_days=14 이지만 days=2 로 캡핑되어 daily_outcomes 슬롯은 2개여야 함
    assert len(body["daily_outcomes"]) == 2


# projects/{id}/summary — seat_id NULL 행이 seats 목록에 email NULL 로 포함 (별도 분리)
async def test_project_summary_null_seat_row_included_with_null_email(
    client: AsyncClient, db_session: AsyncSession, admin_auth_headers: dict
) -> None:
    project = await _seed_project(db_session)
    await _seed_ledger_row(
        db_session, project_id=project.id, seat_id=None, input_tokens=30, output_tokens=5
    )

    resp = await client.get(f"{_BASE}/projects/{project.id}/summary", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    seats_by_seat_id = {s["seat_id"]: s for s in body["seats"]}
    assert None in seats_by_seat_id
    assert seats_by_seat_id[None]["account_email"] is None
    assert seats_by_seat_id[None]["input_tokens"] == 30
    assert seats_by_seat_id[None]["output_tokens"] == 5


# projects/{id}/summary — 비 UUID project_id 처리.
# NOTE(CE-402): 리뷰어는 422 를 기대했으나, path project_id 는 str 이고 서비스가
# 잘못된 형식에 500 대신 빈 집계(200)를 반환하는 것이 문서화된 컨벤션이다
# (observability_service.py:161-169). 실제 동작(200 빈 집계)을 검증한다.
async def test_project_summary_invalid_id_returns_empty_200(
    client: AsyncClient, admin_auth_headers: dict
) -> None:
    resp = await client.get(f"{_BASE}/projects/not-a-uuid/summary", headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_input_tokens"] == 0
    assert body["seats"] == []
    assert body["first_activity_at"] is None
