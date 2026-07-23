import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.rbac import OrganizationMembership
from app.models.user import User

TEST_EMAIL = "test@example.com"


async def _get_user(db: AsyncSession, email: str = TEST_EMAIL) -> User:
    return (await db.execute(select(User).where(User.email == email))).scalar_one()


async def _create_org(db: AsyncSession, name: str = "고객사") -> Organization:
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


async def _set_primary_org(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> None:
    await db.execute(update(User).where(User.id == user_id).values(organization_id=org_id))
    await db.commit()


async def _set_role(db: AsyncSession, user_id: uuid.UUID, role: str) -> None:
    await db.execute(update(User).where(User.id == user_id).values(system_role=role))
    await db.commit()


async def _add_membership(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID) -> None:
    db.add(
        OrganizationMembership(
            user_id=user_id,
            organization_id=org_id,
            org_role="org_member",
            is_active=True,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "테스트 프로젝트", "description": "설명"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "테스트 프로젝트"
    assert body["slug"] == "테스트-프로젝트"
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_create_project_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "테스트"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_project_invalid(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    # 2개 생성
    await client.post(
        "/api/v1/projects/",
        json={"name": "프로젝트 A"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/projects/",
        json={"name": "프로젝트 B"},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/projects/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "조회 테스트"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "조회 테스트"


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "수정 전"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "수정 후"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "수정 후"


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "삭제 대상"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 204

    # 삭제 후 목록에서 사라짐
    list_resp = await client.get("/api/v1/projects/", headers=auth_headers)
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_duplicate_slug_handling(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await client.post(
        "/api/v1/projects/",
        json={"name": "동일 이름"},
        headers=auth_headers,
    )
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "동일 이름"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "동일-이름-1"


# ─── org↔project 스코핑 ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_falls_back_to_primary_org(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    """(a) organization_id 미지정 시 유저의 primary org로 폴백."""
    user = await _get_user(db_session)
    org = await _create_org(db_session, "Primary Org")
    await _set_primary_org(db_session, user.id, org.id)

    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "폴백 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_create_project_with_member_org(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    """(b) 멤버인 org 지정 → 성공."""
    user = await _get_user(db_session)
    org = await _create_org(db_session, "멤버 Org")
    await _add_membership(db_session, user.id, org.id)

    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "멤버 프로젝트", "organization_id": str(org.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_create_project_non_member_org_forbidden(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    """(c) 비멤버 org 지정 → 403."""
    org = await _create_org(db_session, "타 Org")

    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "거부 프로젝트", "organization_id": str(org.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_project_admin_arbitrary_org(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    """(d) control_tower:write 보유자(admin)는 임의 org 지정 가능."""
    user = await _get_user(db_session)
    await _set_role(db_session, user.id, "admin")
    org = await _create_org(db_session, "임의 Org")

    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "관리자 프로젝트", "organization_id": str(org.id)},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["organization_id"] == str(org.id)


@pytest.mark.asyncio
async def test_created_project_exposed_in_control_tower(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    """(e) 생성한 프로젝트가 컨트롤 타워 고객사 프로젝트 목록에 노출된다."""
    user = await _get_user(db_session)
    await _set_role(db_session, user.id, "admin")
    org = await _create_org(db_session, "노출 검증 Org")

    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "노출 프로젝트", "organization_id": str(org.id)},
        headers=auth_headers,
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/control-tower/customers/{org.id}/projects",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()["items"]]
    assert project_id in ids


@pytest.mark.asyncio
async def test_auth_me_exposes_org_and_role(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """/auth/me가 organization_id, system_role 키를 반환한다."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "organization_id" in body
    assert "system_role" in body


# ─────────────────────────────────────────────────────────────────────────────
# superadmin 프로젝트 삭제 경로 (컨트롤타워)
# ─────────────────────────────────────────────────────────────────────────────


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


@pytest.mark.asyncio
async def test_superadmin_deletes_other_project(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """superadmin 은 타 사용자(타 조직) 소유 프로젝트도 삭제할 수 있다."""
    owner_headers, _owner_id = await _register_login(client, "proj_owner@test.com")
    create_resp = await client.post(
        "/api/v1/projects/", json={"name": "타조직 프로젝트"}, headers=owner_headers
    )
    project_id = create_resp.json()["id"]

    super_headers, super_id = await _register_login(client, "proj_super@test.com")
    await _set_role(db_session, uuid.UUID(super_id), "superadmin")

    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=super_headers)
    assert resp.status_code == 204

    # owner 목록에서 사라짐 (soft delete → status=deleted)
    list_resp = await client.get("/api/v1/projects/", headers=owner_headers)
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_non_superadmin_cannot_delete_other_project(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """비-superadmin 은 타 사용자 프로젝트 삭제 불가 (owner 스코프 → 404)."""
    owner_headers, _owner_id = await _register_login(client, "proj_owner2@test.com")
    create_resp = await client.post(
        "/api/v1/projects/", json={"name": "내 프로젝트"}, headers=owner_headers
    )
    project_id = create_resp.json()["id"]

    other_headers, _other_id = await _register_login(client, "proj_other@test.com")
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=other_headers)
    assert resp.status_code == 404

    # 원 소유자 목록에는 그대로 존재
    list_resp = await client.get("/api/v1/projects/", headers=owner_headers)
    assert list_resp.json()["total"] == 1
