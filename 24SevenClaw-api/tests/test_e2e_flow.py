"""E2E 통합 테스트: 유저 등록 → 로그인 → 프로젝트 CRUD 전체 흐름."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_user_project_flow(client: AsyncClient) -> None:
    """회원가입 → 로그인 → 프로젝트 생성/조회/수정/삭제 전체 흐름 검증."""

    # --- 1. 회원가입 ---
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "e2e@example.com",
            "password": "e2epassword123",
            "display_name": "E2E 테스트 유저",
        },
    )
    assert register_resp.status_code == 201
    user = register_resp.json()
    assert user["email"] == "e2e@example.com"
    assert user["display_name"] == "E2E 테스트 유저"
    user_id = user["id"]

    # --- 2. 로그인 ---
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "e2e@example.com", "password": "e2epassword123"},
    )
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # --- 3. 내 정보 확인 ---
    me_resp = await client.get("/api/v1/auth/me", headers=headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["id"] == user_id

    # --- 4. 프로젝트 생성 ---
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "E2E 프로젝트", "description": "통합 테스트용 프로젝트"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    project = create_resp.json()
    project_id = project["id"]
    assert project["name"] == "E2E 프로젝트"
    assert project["slug"] == "e2e-프로젝트"
    assert project["status"] == "active"
    assert project["owner_id"] == user_id

    # --- 5. 프로젝트 목록 조회 ---
    list_resp = await client.get("/api/v1/projects/", headers=headers)
    assert list_resp.status_code == 200
    body = list_resp.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == project_id

    # --- 6. 프로젝트 상세 조회 ---
    get_resp = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["description"] == "통합 테스트용 프로젝트"

    # --- 7. 프로젝트 수정 ---
    update_resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"name": "E2E 수정됨", "description": "수정된 설명"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["name"] == "E2E 수정됨"
    assert updated["description"] == "수정된 설명"

    # --- 8. 프로젝트 삭제 ---
    delete_resp = await client.delete(
        f"/api/v1/projects/{project_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    # --- 9. 삭제 확인 ---
    list_resp2 = await client.get("/api/v1/projects/", headers=headers)
    assert list_resp2.json()["total"] == 0

    # --- 10. 토큰 갱신 ---
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens

    # --- 11. 새 토큰으로 요청 ---
    new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    me_resp2 = await client.get("/api/v1/auth/me", headers=new_headers)
    assert me_resp2.status_code == 200
    assert me_resp2.json()["email"] == "e2e@example.com"


@pytest.mark.asyncio
async def test_cross_user_isolation(client: AsyncClient) -> None:
    """다른 유저의 프로젝트에 접근할 수 없는지 검증."""

    # 유저 A 생성 + 로그인
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "usera@example.com",
            "password": "password123",
            "display_name": "유저 A",
        },
    )
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"email": "usera@example.com", "password": "password123"},
    )
    headers_a = {"Authorization": f"Bearer {login_a.json()['access_token']}"}

    # 유저 B 생성 + 로그인
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "userb@example.com",
            "password": "password123",
            "display_name": "유저 B",
        },
    )
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"email": "userb@example.com", "password": "password123"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

    # 유저 A가 프로젝트 생성
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "A의 프로젝트"},
        headers=headers_a,
    )
    project_id = create_resp.json()["id"]

    # 유저 B가 A의 프로젝트 조회 시 404
    get_resp = await client.get(
        f"/api/v1/projects/{project_id}", headers=headers_b
    )
    assert get_resp.status_code == 404

    # 유저 B의 프로젝트 목록에 A의 프로젝트 없음
    list_resp = await client.get("/api/v1/projects/", headers=headers_b)
    assert list_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """프로젝트 페이지네이션 검증."""
    for i in range(5):
        await client.post(
            "/api/v1/projects/",
            json={"name": f"페이지 프로젝트 {i + 1}"},
            headers=auth_headers,
        )

    # 전체
    all_resp = await client.get("/api/v1/projects/", headers=auth_headers)
    assert all_resp.json()["total"] == 5

    # 2개씩
    page1 = await client.get("/api/v1/projects/?offset=0&limit=2", headers=auth_headers)
    assert len(page1.json()["items"]) == 2
    assert page1.json()["total"] == 5

    page3 = await client.get("/api/v1/projects/?offset=4&limit=2", headers=auth_headers)
    assert len(page3.json()["items"]) == 1


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    """헬스체크 엔드포인트 정상 응답 확인."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "agents_connected" in body
    assert body["agents_connected"] == 0
