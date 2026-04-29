"""인증 엔드포인트 테스트."""

import pytest
from httpx import AsyncClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/auth/me"

TEST_USER = {
    "email": "user@example.com",
    "password": "securepassword123",
    "display_name": "테스트 유저",
}


# --- 회원가입 ---


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    resp = await client.post(REGISTER_URL, json=TEST_USER)
    assert resp.status_code == 201

    data = resp.json()
    assert data["email"] == TEST_USER["email"]
    assert data["display_name"] == TEST_USER["display_name"]
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=TEST_USER)
    resp = await client.post(REGISTER_URL, json=TEST_USER)
    assert resp.status_code == 409
    assert resp.json()["code"] == "EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient) -> None:
    resp = await client.post(
        REGISTER_URL,
        json={"email": "short@example.com", "password": "123", "display_name": "짧은비번"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient) -> None:
    resp = await client.post(
        REGISTER_URL,
        json={"email": "not-an-email", "password": "securepassword123", "display_name": "이름"},
    )
    assert resp.status_code == 422


# --- 로그인 ---


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=TEST_USER)
    resp = await client.post(
        LOGIN_URL,
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=TEST_USER)
    resp = await client.post(
        LOGIN_URL,
        json={"email": TEST_USER["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    resp = await client.post(
        LOGIN_URL,
        json={"email": "nobody@example.com", "password": "somepassword123"},
    )
    assert resp.status_code == 401


# --- 토큰 리프레시 ---


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient) -> None:
    await client.post(REGISTER_URL, json=TEST_USER)
    login_resp = await client.post(
        LOGIN_URL,
        json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
    assert resp.status_code == 200

    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(REFRESH_URL, json={"refresh_token": "invalid-token"})
    assert resp.status_code == 401


# --- GET /me ---


@pytest.mark.asyncio
async def test_me_authenticated(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get(ME_URL, headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "테스트 유저"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient) -> None:
    resp = await client.get(ME_URL)
    # HTTPBearer: 토큰 미제공 시 401 또는 403
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient) -> None:
    resp = await client.get(ME_URL, headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401


# --- OAuth 로그인 ---

OAUTH_URL = "/api/v1/auth/oauth"

OAUTH_NEW_USER = {
    "provider": "github",
    "oauth_id": "gh-12345",
    "email": "oauth@example.com",
    "display_name": "OAuth 유저",
    "avatar_url": "https://example.com/avatar.png",
}


@pytest.mark.asyncio
async def test_oauth_new_user_signup(client: AsyncClient) -> None:
    """OAuth 신규 사용자 자동 가입 + 토큰 발급."""
    resp = await client.post(OAUTH_URL, json=OAUTH_NEW_USER)
    assert resp.status_code == 200

    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # 해당 토큰으로 /me 접근 가능 확인
    me_resp = await client.get(
        ME_URL, headers={"Authorization": f"Bearer {data['access_token']}"}
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == OAUTH_NEW_USER["email"]


@pytest.mark.asyncio
async def test_oauth_existing_user_returns_token(client: AsyncClient) -> None:
    """동일 OAuth provider+id로 재로그인 시 토큰 발급."""
    # 첫 로그인 (자동 가입)
    await client.post(OAUTH_URL, json=OAUTH_NEW_USER)
    # 재로그인
    resp = await client.post(OAUTH_URL, json=OAUTH_NEW_USER)
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_oauth_merge_existing_email(client: AsyncClient) -> None:
    """이메일/비밀번호로 가입된 계정에 OAuth 연결."""
    # 먼저 이메일로 가입
    await client.post(
        REGISTER_URL,
        json={
            "email": "merge@example.com",
            "password": "securepassword123",
            "display_name": "이메일 유저",
        },
    )

    # 동일 이메일로 OAuth 로그인 → 기존 계정에 OAuth 연결
    resp = await client.post(
        OAUTH_URL,
        json={
            "provider": "google",
            "oauth_id": "google-99999",
            "email": "merge@example.com",
            "display_name": "Google 유저",
        },
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()

    # 기존 이메일/비밀번호 로그인도 여전히 가능
    login_resp = await client.post(
        LOGIN_URL,
        json={"email": "merge@example.com", "password": "securepassword123"},
    )
    assert login_resp.status_code == 200


@pytest.mark.asyncio
async def test_oauth_invalid_provider(client: AsyncClient) -> None:
    """지원하지 않는 OAuth provider 거부 (Pydantic 검증)."""
    resp = await client.post(
        OAUTH_URL,
        json={
            "provider": "facebook",
            "oauth_id": "fb-12345",
            "email": "fb@example.com",
            "display_name": "FB 유저",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_oauth_missing_fields(client: AsyncClient) -> None:
    """필수 필드 누락 시 422."""
    resp = await client.post(
        OAUTH_URL,
        json={"provider": "github"},
    )
    assert resp.status_code == 422
