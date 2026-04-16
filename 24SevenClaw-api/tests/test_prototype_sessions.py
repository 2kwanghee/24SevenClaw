import pytest
from httpx import AsyncClient


async def _create_org(client: AsyncClient, headers: dict[str, str]) -> str:
    """테스트용 조직을 생성하고 ID를 반환한다."""
    resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "테스트 회사", "size": "11-50", "industry": "IT"},
        headers=headers,
    )
    return resp.json()["id"]


async def _create_session(
    client: AsyncClient, headers: dict[str, str], org_id: str
) -> dict:
    """테스트용 프로토타입 세션을 생성한다."""
    resp = await client.post(
        "/api/v1/prototype-sessions/",
        json={
            "organization_id": org_id,
            "user_input": {
                "company_name": "테스트 회사",
                "description": "SaaS 구독 관리 서비스를 만들고 싶습니다",
                "business_type": "saas",
            },
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_create_session(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    body = await _create_session(client, auth_headers, org_id)
    assert body["status"] == "pending"
    assert body["organization_id"] == org_id
    assert body["user_input"]["company_name"] == "테스트 회사"


@pytest.mark.asyncio
async def test_create_session_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/prototype-sessions/",
        json={
            "organization_id": "00000000-0000-0000-0000-000000000000",
            "user_input": {"description": "테스트"},
        },
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_sessions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    await _create_session(client, auth_headers, org_id)
    await _create_session(client, auth_headers, org_id)

    resp = await client.get(
        "/api/v1/prototype-sessions/", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_session(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == session["id"]


@pytest.mark.asyncio
async def test_get_session_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get(
        "/api/v1/prototype-sessions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_session_status(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_generate_prototypes(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    resp = await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/generate",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    prototypes = resp.json()
    assert len(prototypes) >= 1
    assert prototypes[0]["solution_type"] == "saas"

    # 상태가 completed로 변경
    status_resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/status",
        headers=auth_headers,
    )
    assert status_resp.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_generate_prototypes_duplicate(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    # 첫 번째 생성
    await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/generate",
        headers=auth_headers,
    )

    # 중복 생성 시도
    resp = await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/generate",
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_prototypes(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    # 프로토타입 생성
    await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/generate",
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


@pytest.mark.asyncio
async def test_select_prototype(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    # 프로토타입 생성
    gen_resp = await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/generate",
        headers=auth_headers,
    )
    prototype_id = gen_resp.json()[0]["id"]

    # 선택
    resp = await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/select",
        json={"prototype_id": prototype_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_selected"] is True


@pytest.mark.asyncio
async def test_delete_session(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    resp = await client.delete(
        f"/api/v1/prototype-sessions/{session['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # 삭제 후 조회 시 404
    get_resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}", headers=auth_headers
    )
    assert get_resp.status_code == 404
