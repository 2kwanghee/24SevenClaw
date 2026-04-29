import pytest
from httpx import AsyncClient


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
