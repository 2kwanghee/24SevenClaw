import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_organization(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.post(
        "/api/v1/organizations/",
        json={
            "company_name": "테스트 회사",
            "size": "11-50",
            "industry": "IT",
            "tech_stack": ["Python", "React"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] == "테스트 회사"
    assert body["size"] == "11-50"
    assert body["industry"] == "IT"
    assert body["tech_stack"] == ["Python", "React"]


@pytest.mark.asyncio
async def test_create_organization_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "테스트"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_organization_invalid(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_my_organization(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    # 먼저 등록
    await client.post(
        "/api/v1/organizations/",
        json={"company_name": "내 회사", "size": "1-10"},
        headers=auth_headers,
    )

    resp = await client.get("/api/v1/organizations/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["company_name"] == "내 회사"
    assert body["size"] == "1-10"


@pytest.mark.asyncio
async def test_get_my_organization_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/organizations/me", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_organization_via_post(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """POST로 등록 후 다시 POST하면 upsert로 수정된다."""
    await client.post(
        "/api/v1/organizations/",
        json={"company_name": "원래 이름", "size": "1-10"},
        headers=auth_headers,
    )

    resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "변경된 이름", "size": "51-200", "industry": "핀테크"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["company_name"] == "변경된 이름"
    assert body["size"] == "51-200"
    assert body["industry"] == "핀테크"

    # GET으로 확인
    get_resp = await client.get("/api/v1/organizations/me", headers=auth_headers)
    assert get_resp.json()["company_name"] == "변경된 이름"
