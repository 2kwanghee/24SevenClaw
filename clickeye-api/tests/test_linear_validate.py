"""Linear API Key 유효성 검증 엔드포인트 테스트 (POST /api/v1/integrations/validate/linear)."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

# 현행 라우트: integrations router(prefix=/integrations) + /validate/linear
ENDPOINT = "/api/v1/integrations/validate/linear"
VALID_PAYLOAD = {"api_key": "lin_api_test", "team_id": "team-uuid-1234"}

# validate_credentials 는 (valid: bool, message: str) 2-튜플을 반환하고,
# 엔드포인트는 IntegrationValidateResponse(valid, message) 로 매핑한다.


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
    """유효한 API 키 + 팀 ID → valid=true, 성공 메시지 반환."""
    with patch(
        "app.services.linear_service.validate_credentials",
        return_value=(True, "인증 성공 (My Team)"),
    ):
        resp = await client.post(ENDPOINT, json=VALID_PAYLOAD, headers=auth_headers_linear)

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert "My Team" in body["message"]


@pytest.mark.asyncio
async def test_validate_linear_invalid_api_key(
    client: AsyncClient, auth_headers_linear: dict[str, str]
) -> None:
    """잘못된 API 키 → valid=false, 에러 메시지 반환."""
    with patch(
        "app.services.linear_service.validate_credentials",
        return_value=(False, "API 키 인증 실패: 401 Unauthorized"),
    ):
        resp = await client.post(ENDPOINT, json=VALID_PAYLOAD, headers=auth_headers_linear)

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "API 키 인증 실패" in body["message"]


@pytest.mark.asyncio
async def test_validate_linear_invalid_team_id(
    client: AsyncClient, auth_headers_linear: dict[str, str]
) -> None:
    """유효한 API 키 + 존재하지 않는 팀 ID → valid=false, 팀 에러 반환."""
    with patch(
        "app.services.linear_service.validate_credentials",
        return_value=(False, "팀 ID를 찾을 수 없습니다. UUID 형식인지 확인하세요."),
    ):
        resp = await client.post(ENDPOINT, json=VALID_PAYLOAD, headers=auth_headers_linear)

    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
    assert "팀 ID를 찾을 수 없습니다" in body["message"]


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
    resp = await client.post(
        ENDPOINT, json={"api_key": "lin_api_test"}, headers=auth_headers_linear
    )
    assert resp.status_code == 422
