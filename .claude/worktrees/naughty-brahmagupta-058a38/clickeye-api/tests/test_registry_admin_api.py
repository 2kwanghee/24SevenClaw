"""Registry Admin API 테스트 — Agent/Skill/MCPServer CRUD."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def _register_and_login(
    client: AsyncClient,
    email: str = "admin@example.com",
    password: str = "adminpass123",
    display_name: str = "관리자",
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
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return {"Authorization": f"Bearer {token}"}, me.json()["id"]


async def _set_role(db: AsyncSession, user_id: str, role: str) -> None:
    stmt = update(User).where(User.id == uuid.UUID(user_id)).values(system_role=role)
    await db.execute(stmt)
    await db.commit()


# ─── 성공 케이스 (3개) ───


@pytest.mark.asyncio
async def test_create_agent_success(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, user_id = await _register_and_login(client)
    await _set_role(db_session, user_id, "admin")

    resp = await client.post(
        "/api/v1/admin/registry/agents",
        json={
            "name": "테스트 에이전트",
            "slug": "test-agent",
            "version": "1.0.0",
            "is_public": True,
            "config_schema": {},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "test-agent"
    assert body["name"] == "테스트 에이전트"


@pytest.mark.asyncio
async def test_create_skill_success(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, user_id = await _register_and_login(client, email="admin2@example.com")
    await _set_role(db_session, user_id, "admin")

    resp = await client.post(
        "/api/v1/admin/registry/skills",
        json={
            "name": "테스트 스킬",
            "slug": "test-skill",
            "version": "0.1.0",
            "is_public": False,
            "config_schema": {},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "test-skill"


@pytest.mark.asyncio
async def test_create_mcp_server_success(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, user_id = await _register_and_login(client, email="admin3@example.com")
    await _set_role(db_session, user_id, "admin")

    resp = await client.post(
        "/api/v1/admin/registry/mcp-servers",
        json={
            "name": "테스트 MCP 서버",
            "slug": "test-mcp-server",
            "version": "2.0.0",
            "body_md": "# MCP 서버\n본문 내용",
            "config_schema": {},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "test-mcp-server"
    assert body["body_md"] == "# MCP 서버\n본문 내용"


# ─── 인증 실패 케이스 (3개) ───


@pytest.mark.asyncio
async def test_list_agents_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/admin/registry/agents")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_skill_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/admin/registry/skills",
        json={"name": "스킬", "slug": "skill", "config_schema": {}},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_mcp_server_insufficient_permission(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, user_id = await _register_and_login(client, email="member@example.com")
    # member 역할은 registry:manage 없음

    resp = await client.post(
        "/api/v1/admin/registry/mcp-servers",
        json={"name": "서버", "slug": "server", "config_schema": {}},
        headers=headers,
    )
    assert resp.status_code == 403


# ─── 유효성 검사 실패 케이스 (3개) ───


@pytest.mark.asyncio
async def test_create_agent_invalid_slug(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, user_id = await _register_and_login(client, email="admin4@example.com")
    await _set_role(db_session, user_id, "admin")

    resp = await client.post(
        "/api/v1/admin/registry/agents",
        json={
            "name": "에이전트",
            "slug": "INVALID SLUG!",  # 대문자 + 공백 + 특수문자
            "config_schema": {},
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_skill_missing_name(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, user_id = await _register_and_login(client, email="admin5@example.com")
    await _set_role(db_session, user_id, "admin")

    resp = await client.post(
        "/api/v1/admin/registry/skills",
        json={
            "slug": "some-skill",
            "config_schema": {},
            # name 누락
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_agent_duplicate_slug(client: AsyncClient, db_session: AsyncSession) -> None:
    headers, user_id = await _register_and_login(client, email="admin6@example.com")
    await _set_role(db_session, user_id, "admin")

    payload = {"name": "중복 에이전트", "slug": "dup-agent", "config_schema": {}}
    await client.post("/api/v1/admin/registry/agents", json=payload, headers=headers)

    resp = await client.post("/api/v1/admin/registry/agents", json=payload, headers=headers)
    assert resp.status_code == 409
