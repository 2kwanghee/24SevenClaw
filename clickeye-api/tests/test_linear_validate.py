"""Linear API Key 유효성 검증 엔드포인트 테스트 (POST /api/v1/integrations/linear/validate)."""
from unittest.mock import patch

import pytest
from httpx import AsyncClient

ENDPOINT = "/api/v1/integrations/linear/validate"
VALID_PAYLOAD = {"api_key": "lin_api_test", "team_id": "team-uuid-1234"}


@pytest.fixture
async def auth_headers_linear(client: AsyncClient) -> dict[str, str]:
    """회원가입 + 로그인 → 인증 헤더 반환."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "linear_test@test.com", "password": "pass1234!", "display_name": "테스터"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "linear_test@test.com", "password": "pass1234!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_validate_linear_valid_credentials(
    client: AsyncClient, auth_headers_linear: dict[str, str]
) -> None:
    """유효한 API 키 + 팀 ID → valid=true, team_name 반환."""
    with patch(
        "app.services.linear_service.validate_credentials_v2",
        return_value=(True, "My Team", None),
    ):
        resp = await client.post(ENDPOINT, json=VALID_PAYLOAD, headers=auth_headers_linear)

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["team_name"] == "My Team"
    assert body["error"] is None


@pytest.mark.asyncio
async def test_validate_linear_invalid_api_key(
    client: AsyncClient, auth_headers_linear: dict[str, str]
) -> None:
    """잘못된 API 키 → valid=false, error 메시지 반환."""
    with patch(
        "app.services.linear_service.validate_credentials_v2",
        return_value=(False, None, "API Key가 유효하지 않습니다"),
    ):
        resp = await client.post(ENDPOINT, json=VALID_PAYLOAD, headers=auth_headers_linear)

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["error"] == "API Key가 유효하지 않습니다"
    assert body["team_name"] is None


@pytest.mark.asyncio
async def test_validate_linear_invalid_team_id(
    client: AsyncClient, auth_headers_linear: dict[str, str]
) -> None:
    """유효한 API 키 + 존재하지 않는 팀 ID → valid=false, 팀 에러 반환."""
    with patch(
        "app.services.linear_service.validate_credentials_v2",
        return_value=(False, None, "팀 ID를 찾을 수 없습니다"),
    ):
        resp = await client.post(ENDPOINT, json=VALID_PAYLOAD, headers=auth_headers_linear)

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert body["error"] == "팀 ID를 찾을 수 없습니다"
    assert body["team_name"] is None


@pytest.mark.asyncio
async def test_validate_linear_unauthenticated(client: AsyncClient) -> None:
    """인증 없이 요청 → 401/403."""
    resp = await client.post(ENDPOINT, json=VALID_PAYLOAD)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_validate_linear_missing_fields(
    client: AsyncClient, auth_headers_linear: dict[str, str]
) -> None:
    """필수 필드 누락 → 422."""
    resp = await client.post(ENDPOINT, json={"api_key": "lin_api_test"}, headers=auth_headers_linear)
    assert resp.status_code == 422
