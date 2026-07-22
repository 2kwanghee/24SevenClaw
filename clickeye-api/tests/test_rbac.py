import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.user import User


async def _register_and_login(
    client: AsyncClient,
    email: str,
    display_name: str = "test",
    password: str = "pw12345678",
) -> tuple[dict[str, str], str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return headers, me.json()["id"]


async def _set_role(db: AsyncSession, user_id: str, role: str) -> None:
    stmt = update(User).where(User.id == uuid.UUID(user_id)).values(system_role=role)
    await db.execute(stmt)
    await db.commit()


async def _create_org(db: AsyncSession) -> str:
    org = Organization(company_name="test org")
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return str(org.id)


@pytest.mark.asyncio
async def test_get_permissions_member(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get("/api/v1/rbac/permissions", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["system_role"] == "member"
    assert "project:create" in body["permissions"]
    assert "rbac:manage" not in body["permissions"]


@pytest.mark.asyncio
async def test_get_permissions_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/rbac/permissions")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_permissions_superadmin(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, uid = await _register_and_login(client, "super@test.com")
    await _set_role(db_session, uid, "superadmin")
    resp = await client.get("/api/v1/rbac/permissions", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["system_role"] == "superadmin"
    assert "rbac:manage" in body["permissions"]


@pytest.mark.asyncio
async def test_list_users_forbidden_for_member(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/admin/users", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_success_for_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, uid = await _register_and_login(client, "admin@test.com")
    await _set_role(db_session, uid, "admin")
    resp = await client.get("/api/v1/admin/users", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_users_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/users")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_role_success(client: AsyncClient, db_session: AsyncSession) -> None:
    sa_headers, _ = await _register_and_login(client, "sa@test.com")
    await _set_role(db_session, _, "superadmin")
    _, target_id = await _register_and_login(client, "target@test.com")

    resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"system_role": "admin"},
        headers=sa_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["system_role"] == "admin"


@pytest.mark.asyncio
async def test_update_role_forbidden_for_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, uid = await _register_and_login(client, "admin2@test.com")
    await _set_role(db_session, uid, "admin")
    _, target_id = await _register_and_login(client, "target2@test.com")

    resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"system_role": "viewer"},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_role_invalid(client: AsyncClient, db_session: AsyncSession) -> None:
    sa_headers, _ = await _register_and_login(client, "sa2@test.com")
    await _set_role(db_session, _, "superadmin")
    _, target_id = await _register_and_login(client, "target3@test.com")

    resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"system_role": "nonexistent"},
        headers=sa_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_org_members_crud(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, admin_id = await _register_and_login(client, "orgadmin@test.com")
    await _set_role(db_session, admin_id, "admin")
    _, member_id = await _register_and_login(client, "orgmember@test.com")
    org_id = await _create_org(db_session)

    resp = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": member_id, "org_role": "org_member"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["org_role"] == "org_member"

    resp = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.delete(
        f"/api/v1/organizations/{org_id}/members/{member_id}",
        headers=headers,
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_org_member_duplicate(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, admin_id = await _register_and_login(client, "dup_admin@test.com")
    await _set_role(db_session, admin_id, "admin")
    _, member_id = await _register_and_login(client, "dup_member@test.com")
    org_id = await _create_org(db_session)

    await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": member_id, "org_role": "org_member"},
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": member_id, "org_role": "org_member"},
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_org_members_forbidden_for_member(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(db_session)
    resp = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_log_success(client: AsyncClient, db_session: AsyncSession) -> None:
    sa_headers, sa_id = await _register_and_login(client, "audit_sa@test.com")
    await _set_role(db_session, sa_id, "superadmin")
    _, target_id = await _register_and_login(client, "audit_target@test.com")

    await client.patch(
        f"/api/v1/admin/users/{target_id}/role",
        json={"system_role": "admin"},
        headers=sa_headers,
    )

    resp = await client.get("/api/v1/admin/audit-log", headers=sa_headers)
    assert resp.status_code == 200
    logs = resp.json()
    assert len(logs) >= 1
    assert logs[0]["action"] == "assign_system_role"


@pytest.mark.asyncio
async def test_audit_log_forbidden_for_member(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/admin/audit-log", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_org_member_seals_null_primary_org(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """(f) primary organization_id가 NULL인 유저를 멤버로 추가하면 primary가 봉합된다."""
    headers, admin_id = await _register_and_login(client, "seal_admin@test.com")
    await _set_role(db_session, admin_id, "admin")
    _, target_id = await _register_and_login(client, "seal_target@test.com")
    org_id = await _create_org(db_session)

    # 사전 조건: 대상 유저의 primary org는 NULL
    target = (
        await db_session.execute(select(User).where(User.id == uuid.UUID(target_id)))
    ).scalar_one()
    assert target.organization_id is None

    resp = await client.post(
        f"/api/v1/organizations/{org_id}/members",
        json={"user_id": target_id, "org_role": "org_member"},
        headers=headers,
    )
    assert resp.status_code == 201

    db_session.expire_all()
    target = (
        await db_session.execute(select(User).where(User.id == uuid.UUID(target_id)))
    ).scalar_one()
    assert str(target.organization_id) == org_id


# ─────────────────────────────────────────────────────────────────────────────
# 사용자 삭제 (soft/hard)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_user_soft_by_admin(client: AsyncClient, db_session: AsyncSession) -> None:
    """소프트 삭제(기본): admin 이 member 를 비활성화한다."""
    headers, _admin_id = await _register_and_login(client, "del_admin@test.com")
    await _set_role(db_session, _admin_id, "admin")
    _, target_id = await _register_and_login(client, "del_target@test.com")

    resp = await client.delete(f"/api/v1/admin/users/{target_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "soft"
    assert body["deleted"] is False
    assert body["is_active"] is False

    # is_active 반영 확인
    db_session.expire_all()
    target = (
        await db_session.execute(select(User).where(User.id == uuid.UUID(target_id)))
    ).scalar_one()
    assert target.is_active is False


@pytest.mark.asyncio
async def test_delete_user_hard_by_superadmin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """하드 삭제: superadmin 이 사용자를 물리 삭제한다."""
    headers, super_id = await _register_and_login(client, "hard_super@test.com")
    await _set_role(db_session, super_id, "superadmin")
    _, target_id = await _register_and_login(client, "hard_target@test.com")

    resp = await client.delete(
        f"/api/v1/admin/users/{target_id}?hard=true", headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "hard"
    assert body["deleted"] is True

    # 레코드가 물리 삭제됨
    db_session.expire_all()
    target = (
        await db_session.execute(select(User).where(User.id == uuid.UUID(target_id)))
    ).scalar_one_or_none()
    assert target is None


@pytest.mark.asyncio
async def test_delete_user_forbidden_for_member(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """비-admin(member) 는 사용자 삭제 불가 (403)."""
    _, target_id = await _register_and_login(client, "victim@test.com")
    resp = await client.delete(f"/api/v1/admin/users/{target_id}", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_hard_forbidden_for_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """admin(비-superadmin) 은 하드 삭제 불가 (403)."""
    headers, admin_id = await _register_and_login(client, "hard_admin@test.com")
    await _set_role(db_session, admin_id, "admin")
    _, target_id = await _register_and_login(client, "hard_admin_target@test.com")

    resp = await client.delete(
        f"/api/v1/admin/users/{target_id}?hard=true", headers=headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_self_blocked(client: AsyncClient, db_session: AsyncSession) -> None:
    """자기 자신 삭제 금지 (400)."""
    headers, admin_id = await _register_and_login(client, "self_admin@test.com")
    await _set_role(db_session, admin_id, "admin")

    resp = await client.delete(f"/api/v1/admin/users/{admin_id}", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "CANNOT_DELETE_SELF"


@pytest.mark.asyncio
async def test_delete_last_superadmin_blocked(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """마지막 superadmin 삭제 금지 (409)."""
    headers, super_id = await _register_and_login(client, "last_super@test.com")
    await _set_role(db_session, super_id, "superadmin")

    # 유일한 superadmin 이 자기 자신을 삭제 시도 → last-superadmin 가드가 우선 차단
    resp = await client.delete(f"/api/v1/admin/users/{super_id}", headers=headers)
    assert resp.status_code == 409
    assert resp.json()["code"] == "LAST_SUPERADMIN"
