"""프로젝트별 Linear 자격증명 CRUD 테스트.

라우트: PUT/GET/DELETE /api/v1/integrations/projects/{project_id}/linear-credentials
소유권 가드(_require_project_access): 소유자 또는 admin+ 만 접근 — IDOR 차단(리뷰 HIGH 반영).
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

BASE = "/api/v1/integrations/projects"
API_KEY = "lin_api_secret_plaintext_1234567890"
TEAM_ID = "team-uuid-abcd-1234"


def _url(project_id: str) -> str:
    return f"{BASE}/{project_id}/linear-credentials"


async def _register_login(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234!", "display_name": "테스터"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "pass1234!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
async def owner_ctx(client: AsyncClient) -> tuple[dict[str, str], str]:
    """소유자 인증 헤더 + 그 사용자가 소유한 프로젝트 id."""
    headers = await _register_login(client, "plc_owner@test.com")
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "PLC 테스트 프로젝트"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return headers, resp.json()["id"]


@pytest.mark.asyncio
async def test_put_registers_credentials_and_masks_key(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """소유 프로젝트 PUT 등록 → 200, 응답은 마스킹 키·팀 ID, 평문 키 무노출."""
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
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
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """등록 후 GET → 마스킹 키·팀 ID 반환, 평문 무노출."""
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    resp = await client.get(_url(project_id), headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["team_id"] == TEAM_ID
    assert "****" in body["api_key_masked"]
    assert API_KEY not in resp.text


@pytest.mark.asyncio
async def test_get_missing_returns_404(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """소유 프로젝트라도 자격증명 미등록이면 GET → 404."""
    headers, project_id = owner_ctx
    resp = await client.get(_url(project_id), headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_removes_credentials(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """DELETE → 204, 이후 GET 404."""
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    resp = await client.delete(_url(project_id), headers=headers)
    assert resp.status_code == 204
    follow = await client.get(_url(project_id), headers=headers)
    assert follow.status_code == 404


@pytest.mark.asyncio
async def test_non_owner_cannot_touch_credentials(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """IDOR 차단 — 타 사용자는 소유자 프로젝트 자격증명에 PUT/GET/DELETE 전부 404."""
    owner_headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=owner_headers,
    )
    intruder = await _register_login(client, "plc_intruder@test.com")
    put_resp = await client.put(
        _url(project_id),
        json={"api_key": "lin_api_evil_overwrite_0000000000", "team_id": "evil-team"},
        headers=intruder,
    )
    assert put_resp.status_code == 404
    get_resp = await client.get(_url(project_id), headers=intruder)
    assert get_resp.status_code == 404
    del_resp = await client.delete(_url(project_id), headers=intruder)
    assert del_resp.status_code == 404
    # 소유자 데이터는 훼손되지 않았다
    intact = await client.get(_url(project_id), headers=owner_headers)
    assert intact.status_code == 200
    assert intact.json()["team_id"] == TEAM_ID


@pytest.mark.asyncio
async def test_unknown_project_returns_404(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """존재하지 않는 프로젝트 id → 404 (소유권 가드가 존재 여부를 숨김)."""
    headers, _ = owner_ctx
    resp = await client.put(
        _url(str(uuid4())),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_requires_auth(client: AsyncClient) -> None:
    """인증 헤더 없이 PUT → 401."""
    resp = await client.put(
        _url(str(uuid4())),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
    )
    assert resp.status_code == 401
