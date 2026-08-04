"""CE-337 — 프로젝트 스코프 인테이크 역조회 API + 인테이크 프로젝트 세션 차단 테스트."""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_event import DeliveryEvent
from app.models.intake import IntakeRequest, IntakeServiceKey
from app.models.organization import Organization
from app.models.project import Project


async def _register_login(
    client: AsyncClient, email: str, password: str = "pw12345678"
) -> tuple[dict[str, str], str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": email.split("@")[0]},
    )
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return headers, me.json()["id"]


async def _create_project(
    client: AsyncClient, headers: dict[str, str], name: str = "인테이크 프로젝트"
) -> str:
    resp = await client.post("/api/v1/projects/", json={"name": name}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _set_project_type(db: AsyncSession, project_id: str, project_type: str) -> None:
    await db.execute(
        update(Project).where(Project.id == uuid.UUID(project_id)).values(project_type=project_type)
    )
    await db.commit()


async def _seed_intake(
    db: AsyncSession,
    project_id: str,
    *,
    with_events: bool = False,
) -> IntakeRequest:
    """프로젝트에 연결된 인테이크(+선택 타임라인 이벤트)를 시드한다."""
    org = Organization(company_name="테스트고객사")
    db.add(org)
    await db.flush()
    key = IntakeServiceKey(
        name="외부수주서비스",
        key_hash=hashlib.sha256(uuid.uuid4().hex.encode()).hexdigest(),
        organization_id=org.id,
    )
    db.add(key)
    await db.flush()
    intake = IntakeRequest(
        service_key_id=key.id,
        input_type="structured",
        title="쇼핑몰 구축",
        payload={"기능": ["회원가입", "결제"]},
        normalized_text="쇼핑몰 구축 요구사항",
        status="accepted",
        refine_status="refined",
        tickets_status="issued",
        tickets=[{"key": "T1", "identifier": "CE-500", "issue_id": "abc", "title": "회원가입"}],
        project_id=uuid.UUID(project_id),
    )
    db.add(intake)
    await db.flush()

    if with_events:
        base = datetime.now(UTC)
        for i, et in enumerate(["received", "refined", "accepted", "issued"]):
            db.add(
                DeliveryEvent(
                    intake_id=intake.id,
                    project_id=uuid.UUID(project_id),
                    event_type=et,
                    actor_type="system",
                    detail=f"{et} 전이",
                    created_at=base + timedelta(seconds=i),
                )
            )
    await db.commit()
    await db.refresh(intake)
    return intake


# ── GET /projects/{id}/intake ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_project_intake_ok(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    project_id = await _create_project(client, auth_headers)
    intake = await _seed_intake(db_session, project_id)

    resp = await client.get(f"/api/v1/projects/{project_id}/intake", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == str(intake.id)
    assert body["project_id"] == project_id
    assert body["tickets_status"] == "issued"
    assert body["tickets"][0]["identifier"] == "CE-500"


@pytest.mark.asyncio
async def test_get_project_intake_404_when_no_intake(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """인테이크 유래가 아닌 수동 프로젝트 → 연결된 인테이크 없음 → 404."""
    project_id = await _create_project(client, auth_headers, name="수동 프로젝트")
    resp = await client.get(f"/api/v1/projects/{project_id}/intake", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_project_intake_other_user_forbidden(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """타 사용자 프로젝트 접근 → owner 스코프로 404(존재 은닉)."""
    project_id = await _create_project(client, auth_headers)
    await _seed_intake(db_session, project_id)

    other_headers, _ = await _register_login(client, "intake_other@test.com")
    resp = await client.get(f"/api/v1/projects/{project_id}/intake", headers=other_headers)
    assert resp.status_code == 404


# ── GET /projects/{id}/intake/timeline ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_project_intake_timeline_ok(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    project_id = await _create_project(client, auth_headers)
    intake = await _seed_intake(db_session, project_id, with_events=True)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/intake/timeline", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["intake_id"] == str(intake.id)
    assert body["tickets_status"] == "issued"
    # 발생 순서(created_at asc) 유지
    assert [e["event_type"] for e in body["events"]] == [
        "received",
        "refined",
        "accepted",
        "issued",
    ]


@pytest.mark.asyncio
async def test_get_project_intake_timeline_404_when_no_intake(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    project_id = await _create_project(client, auth_headers, name="수동 프로젝트")
    resp = await client.get(
        f"/api/v1/projects/{project_id}/intake/timeline", headers=auth_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_project_intake_timeline_other_user_forbidden(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    project_id = await _create_project(client, auth_headers)
    await _seed_intake(db_session, project_id, with_events=True)

    other_headers, _ = await _register_login(client, "intake_other2@test.com")
    resp = await client.get(
        f"/api/v1/projects/{project_id}/intake/timeline", headers=other_headers
    )
    assert resp.status_code == 404


# ── 세션 생성 차단 (CE-336 보완) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session_blocked_for_intake_project(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """인테이크 유래 프로젝트(project_type=intake)는 세션 생성 409 거부."""
    project_id = await _create_project(client, auth_headers)
    await _set_project_type(db_session, project_id, "intake")

    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "수동 세션 시도", "description": "차단되어야 함"},
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_session_ok_for_normal_project(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """비인테이크(수동) 프로젝트는 세션 생성 정상 동작(무회귀)."""
    project_id = await _create_project(client, auth_headers, name="수동 프로젝트")
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "정상 세션", "description": "생성되어야 함"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
