"""중앙 계약 관리 API 테스트."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.central_contract import CentralContract
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


async def _admin_headers(client: AsyncClient, db: AsyncSession) -> dict[str, str]:
    """admin 역할 헤더 생성."""
    headers, user_id = await _register_and_login(
        client, "admin-contract@example.com", "contract-admin"
    )
    await _set_role(db, user_id, "admin")
    return headers


async def _seed_contract(db: AsyncSession) -> CentralContract:
    """테스트용 중앙 계약 직접 삽입."""
    contract = CentralContract(
        slug=f"test-contract-{uuid.uuid4().hex[:8]}",
        contract_type="execution",
        source="central",
        version="1.0.0",
        content={"max_tokens": 100000, "model": "claude-4", "timeout": 300},
        description="테스트 계약",
        is_locked=True,
        allowed_overrides=["max_tokens", "timeout"],
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)
    return contract


# ── CentralContract CRUD ──


@pytest.mark.asyncio
async def test_create_contract(client: AsyncClient, db_session: AsyncSession) -> None:
    """계약 생성 성공."""
    headers = await _admin_headers(client, db_session)

    resp = await client.post(
        "/api/v1/contracts/",
        json={
            "slug": "my-contract",
            "contract_type": "execution",
            "source": "central",
            "content": {"model": "claude-4"},
            "allowed_overrides": ["model"],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "my-contract"
    assert data["contract_type"] == "execution"
    assert data["allowed_overrides"] == ["model"]


@pytest.mark.asyncio
async def test_create_contract_duplicate_slug(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """중복 slug 생성 시 409."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    resp = await client.post(
        "/api/v1/contracts/",
        json={
            "slug": contract.slug,
            "contract_type": "execution",
            "source": "central",
        },
        headers=headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_contracts(client: AsyncClient, db_session: AsyncSession) -> None:
    """계약 목록 조회."""
    headers = await _admin_headers(client, db_session)
    await _seed_contract(db_session)

    resp = await client.get("/api/v1/contracts/", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_contract(client: AsyncClient, db_session: AsyncSession) -> None:
    """계약 단건 조회."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    resp = await client.get(f"/api/v1/contracts/{contract.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(contract.id)


@pytest.mark.asyncio
async def test_get_contract_not_found(client: AsyncClient, db_session: AsyncSession) -> None:
    """없는 계약 조회 시 404."""
    headers = await _admin_headers(client, db_session)
    resp = await client.get(f"/api/v1/contracts/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_contract(client: AsyncClient, db_session: AsyncSession) -> None:
    """계약 수정 성공."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    resp = await client.put(
        f"/api/v1/contracts/{contract.id}",
        json={"version": "2.0.0", "description": "수정된 계약"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "2.0.0"
    assert data["description"] == "수정된 계약"


@pytest.mark.asyncio
async def test_delete_contract(client: AsyncClient, db_session: AsyncSession) -> None:
    """계약 삭제 성공."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    resp = await client.delete(f"/api/v1/contracts/{contract.id}", headers=headers)
    assert resp.status_code == 204

    # 삭제 후 조회 시 404
    resp2 = await client.get(f"/api/v1/contracts/{contract.id}", headers=headers)
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_contract_unauthorized(client: AsyncClient) -> None:
    """인증 없이 접근 시 401."""
    resp = await client.get("/api/v1/contracts/")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_contract_forbidden_member(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """member 역할로 접근 시 403."""
    resp = await client.get("/api/v1/contracts/", headers=auth_headers)
    assert resp.status_code == 403


# ── Customer Override ──


@pytest.mark.asyncio
async def test_apply_contract_to_project(client: AsyncClient, db_session: AsyncSession) -> None:
    """프로젝트에 계약 적용 (오버라이드 생성)."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    # 프로젝트 생성
    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "계약 테스트 프로젝트"},
        headers=headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 오버라이드 생성 (허용 필드)
    resp = await client.post(
        f"/api/v1/projects/{project_id}/contract-overrides/",
        json={
            "central_contract_id": str(contract.id),
            "override_content": {"max_tokens": 50000},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["central_contract_id"] == str(contract.id)
    assert data["override_content"]["max_tokens"] == 50000


@pytest.mark.asyncio
async def test_override_disallowed_field(client: AsyncClient, db_session: AsyncSession) -> None:
    """allowed_overrides 외 필드 수정 시 422."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "제한 테스트"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    # "model" 필드는 allowed_overrides에 없음
    resp = await client.post(
        f"/api/v1/projects/{project_id}/contract-overrides/",
        json={
            "central_contract_id": str(contract.id),
            "override_content": {"model": "gpt-4"},
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_override(client: AsyncClient, db_session: AsyncSession) -> None:
    """오버라이드 수정 성공 (허용 필드만)."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "수정 테스트"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    # 오버라이드 생성
    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/contract-overrides/",
        json={
            "central_contract_id": str(contract.id),
            "override_content": {"max_tokens": 50000},
        },
        headers=headers,
    )
    override_id = create_resp.json()["id"]

    # 허용 필드로 수정
    resp = await client.patch(
        f"/api/v1/projects/{project_id}/contract-overrides/{override_id}",
        json={"override_content": {"timeout": 600}},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["override_content"]["timeout"] == 600


@pytest.mark.asyncio
async def test_update_override_disallowed(client: AsyncClient, db_session: AsyncSession) -> None:
    """오버라이드 수정 시 비허용 필드 → 422."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "비허용 테스트"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/contract-overrides/",
        json={
            "central_contract_id": str(contract.id),
            "override_content": {"max_tokens": 50000},
        },
        headers=headers,
    )
    override_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/projects/{project_id}/contract-overrides/{override_id}",
        json={"override_content": {"model": "gpt-4"}},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_project_overrides(client: AsyncClient, db_session: AsyncSession) -> None:
    """프로젝트별 오버라이드 목록 조회."""
    headers = await _admin_headers(client, db_session)
    contract = await _seed_contract(db_session)

    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "목록 테스트"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/contract-overrides/",
        json={
            "central_contract_id": str(contract.id),
            "override_content": {"max_tokens": 50000},
        },
        headers=headers,
    )

    resp = await client.get(
        f"/api/v1/projects/{project_id}/contract-overrides/",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


# ── Sync ──


@pytest.mark.asyncio
async def test_sync_contracts_no_agents(client: AsyncClient, db_session: AsyncSession) -> None:
    """연결된 Agent 없을 때 sync → 0건."""
    headers = await _admin_headers(client, db_session)

    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "동기화 테스트"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/contracts/sync",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced_count"] == 0
    assert data["agent_ids"] == []


# ── Audit Log ──


@pytest.mark.asyncio
async def test_audit_log_created_on_contract_create(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """계약 생성 시 감사 로그 기록."""
    headers = await _admin_headers(client, db_session)

    await client.post(
        "/api/v1/contracts/",
        json={
            "slug": "audit-test",
            "contract_type": "execution",
            "source": "central",
        },
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/contracts/audit?change_type=create_contract",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["change_type"] == "create_contract"
