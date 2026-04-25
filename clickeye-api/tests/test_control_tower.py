"""컨트롤 타워 API 테스트."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
CT_URL = "/api/v1/control-tower"

ADMIN_USER = {
    "email": "admin@clickeye.io",
    "password": "adminpassword1",
    "display_name": "ClickEye 관리자",
}
MEMBER_USER = {
    "email": "member@example.com",
    "password": "memberpassword1",
    "display_name": "일반 회원",
}


async def _register_and_login(client: AsyncClient, payload: dict) -> str:
    await client.post(REGISTER_URL, json=payload)
    resp = await client.post(LOGIN_URL, json={"email": payload["email"], "password": payload["password"]})
    return resp.json()["access_token"]


async def _make_admin(db: AsyncSession, email: str) -> None:
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.system_role = "admin"  # type: ignore[assignment]
    await db.commit()


async def _seed_customer(db: AsyncSession, name: str = "테스트 고객사") -> Organization:
    org = Organization(
        id=uuid.uuid4(),
        company_name=name,
        org_type="customer",
        customer_status="active",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _seed_project(db: AsyncSession, owner_id: uuid.UUID, org_id: uuid.UUID, name: str = "NMS") -> Project:
    proj = Project(
        id=uuid.uuid4(),
        owner_id=owner_id,
        organization_id=org_id,
        name=name,
        slug=name.lower(),
        status="active",
        settings={},
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return proj


# ─── 비관리자 접근 거부 ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_control_tower_requires_admin(client: AsyncClient) -> None:
    """비관리자(member)는 컨트롤 타워에 접근할 수 없다."""
    token = await _register_and_login(client, MEMBER_USER)
    resp = await client.get(
        f"{CT_URL}/customers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_control_tower_requires_auth(client: AsyncClient) -> None:
    """인증 없이 접근하면 401."""
    resp = await client.get(f"{CT_URL}/customers")
    assert resp.status_code == 401


# ─── 관리자 — 고객사 목록 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_customers_empty(client: AsyncClient, db_session: AsyncSession) -> None:
    """고객사 없을 때 빈 목록."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])

    resp = await client.get(
        f"{CT_URL}/customers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_customers(client: AsyncClient, db_session: AsyncSession) -> None:
    """고객사 목록 조회 — 집계 포함."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])
    await _seed_customer(db_session, "A 고객사")
    await _seed_customer(db_session, "B 고객사")

    resp = await client.get(
        f"{CT_URL}/customers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert all("project_count" in item for item in data["items"])


# ─── 관리자 — 고객사 상세 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_customer_detail(client: AsyncClient, db_session: AsyncSession) -> None:
    """고객사 상세 조회."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])
    org = await _seed_customer(db_session, "NMS 고객사")

    resp = await client.get(
        f"{CT_URL}/customers/{org.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["company_name"] == "NMS 고객사"
    assert data["org_type"] == "customer"
    assert data["customer_status"] == "active"


@pytest.mark.asyncio
async def test_get_customer_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    """존재하지 않는 고객사 — 404."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])

    resp = await client.get(
        f"{CT_URL}/customers/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


# ─── 관리자 — 고객사 프로젝트 목록 ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_customer_projects(client: AsyncClient, db_session: AsyncSession) -> None:
    """고객사의 프로젝트 목록 조회."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])

    from sqlalchemy import select
    admin = (await db_session.execute(select(User).where(User.email == ADMIN_USER["email"]))).scalar_one()
    org = await _seed_customer(db_session)
    await _seed_project(db_session, admin.id, org.id, "NMS 프로젝트")

    resp = await client.get(
        f"{CT_URL}/customers/{org.id}/projects",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "NMS 프로젝트"


# ─── 관리자 — 고객사 상태 변경 ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_customer_status(client: AsyncClient, db_session: AsyncSession) -> None:
    """고객사를 일시정지로 변경."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])
    org = await _seed_customer(db_session)

    resp = await client.post(
        f"{CT_URL}/customers/{org.id}/status",
        json={"status": "paused"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["customer_status"] == "paused"


@pytest.mark.asyncio
async def test_set_customer_status_invalid(client: AsyncClient, db_session: AsyncSession) -> None:
    """허용되지 않는 상태값 — 422."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])
    org = await _seed_customer(db_session)

    resp = await client.post(
        f"{CT_URL}/customers/{org.id}/status",
        json={"status": "invalid_status"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


# ─── 관리자 — 프로젝트 이동 ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transfer_project(client: AsyncClient, db_session: AsyncSession) -> None:
    """프로젝트를 다른 고객사로 이동."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])

    from sqlalchemy import select
    admin = (await db_session.execute(select(User).where(User.email == ADMIN_USER["email"]))).scalar_one()
    org_a = await _seed_customer(db_session, "A 고객사")
    org_b = await _seed_customer(db_session, "B 고객사")
    proj = await _seed_project(db_session, admin.id, org_a.id)

    resp = await client.post(
        f"{CT_URL}/projects/{proj.id}/transfer",
        json={"to_organization_id": str(org_b.id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["organization_id"] == str(org_b.id)


# ─── 프로젝트 개요 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_project_overview(client: AsyncClient, db_session: AsyncSession) -> None:
    """프로젝트 종합 정보 조회."""
    token = await _register_and_login(client, ADMIN_USER)
    await _make_admin(db_session, ADMIN_USER["email"])

    from sqlalchemy import select
    admin = (await db_session.execute(select(User).where(User.email == ADMIN_USER["email"]))).scalar_one()
    org = await _seed_customer(db_session)
    proj = await _seed_project(db_session, admin.id, org.id)

    resp = await client.get(
        f"{CT_URL}/projects/{proj.id}/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == proj.name
    assert data["session_count"] == 0
    assert data["active_session_count"] == 0
