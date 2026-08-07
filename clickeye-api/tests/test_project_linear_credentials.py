"""프로젝트별 Linear 자격증명 CRUD 테스트.

라우트: PUT/GET/DELETE /api/v1/integrations/projects/{project_id}/linear-credentials
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

BASE = "/api/v1/integrations/projects"
API_KEY = "lin_api_secret_plaintext_1234567890"
TEAM_ID = "team-uuid-abcd-1234"


def _url(project_id: str) -> str:
    return f"{BASE}/{project_id}/linear-credentials"


@pytest.fixture
async def auth_headers_plc(client: AsyncClient) -> dict[str, str]:
    """회원가입 + 로그인 → 인증 헤더 반환."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": "plc_test@test.com", "password": "pass1234!", "display_name": "테스터"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "plc_test@test.com", "password": "pass1234!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.asyncio
async def test_put_registers_credentials_and_masks_key(
    client: AsyncClient, auth_headers_plc: dict[str, str]
) -> None:
    """PUT 등록 → 200, 응답은 마스킹 키·팀 ID, 평문 키 무노출."""
    project_id = str(uuid4())
    resp = await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=auth_headers_plc,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["team_id"] == TEAM_ID
    assert body["updated_at"]
    # 평문 키는 절대 반환되지 않는다
    assert API_KEY not in resp.text
    assert "****" in body["api_key_masked"]


@pytest.mark.asyncio
async def test_get_returns_masked_credentials(
    client: AsyncClient, auth_headers_plc: dict[str, str]
) -> None:
    """등록 후 GET → 마스킹 키·팀 ID 반환, 평문 무노출."""
    project_id = str(uuid4())
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=auth_headers_plc,
    )
    resp = await client.get(_url(project_id), headers=auth_headers_plc)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["team_id"] == TEAM_ID
    assert "****" in body["api_key_masked"]
    assert API_KEY not in resp.text


@pytest.mark.asyncio
async def test_get_missing_returns_404(
    client: AsyncClient, auth_headers_plc: dict[str, str]
) -> None:
    """미등록 프로젝트 GET → 404."""
    resp = await client.get(_url(str(uuid4())), headers=auth_headers_plc)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_removes_credentials(
    client: AsyncClient, auth_headers_plc: dict[str, str]
) -> None:
    """DELETE → 204, 이후 GET 404."""
    project_id = str(uuid4())
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=auth_headers_plc,
    )
    resp = await client.delete(_url(project_id), headers=auth_headers_plc)
    assert resp.status_code == 204
    follow = await client.get(_url(project_id), headers=auth_headers_plc)
    assert follow.status_code == 404


@pytest.mark.asyncio
async def test_put_requires_auth(client: AsyncClient) -> None:
    """인증 헤더 없이 PUT → 401."""
    resp = await client.put(
        _url(str(uuid4())),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
    )
    assert resp.status_code == 401
