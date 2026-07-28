"""구독 시트 등록·배정·머신 수령 테스트 (다프로젝트화 P4).

평문 토큰은 단언에 필요한 최소 범위에서만 다루고, 응답 본문에 토큰이 새지 않는지를
명시적으로 검사한다.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials

SEAT_URL = "/api/v1/me/anthropic-credentials/seat"
CREDS_URL = "/api/v1/me/anthropic-credentials/"
SEAT_TOKEN_URL = "/api/v1/governance/seat-token"

OWNER_TOKEN = "sk-ant-oat01-owner-seat-token"
MEMBER_TOKEN = "sk-ant-oat01-member-seat-token"


async def _register_user(client: AsyncClient, email: str) -> dict[str, str]:
    """새 사용자 등록 후 인증 헤더 반환."""
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123", "display_name": email},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _user_id(db: AsyncSession, email: str) -> uuid.UUID:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    return user.id  # type: ignore[return-value]


async def _create_project(client: AsyncClient, headers: dict[str, str], name: str) -> str:
    resp = await client.post("/api/v1/projects/", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


# ── 등록/조회/교체/해제 ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seat_register_get_replace_delete(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.put(SEAT_URL, json={"oauth_token": OWNER_TOKEN}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    seat_id = body["seat_id"]
    assert body["seat_status"] == "active"
    # 응답에 토큰이 어떤 형태로도 실리지 않아야 한다(마스킹 포함 미노출).
    assert OWNER_TOKEN not in resp.text
    assert "token" not in body

    resp = await client.get(SEAT_URL, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["seat_id"] == seat_id
    assert OWNER_TOKEN not in resp.text

    # 교체 — 동일 시트 행이 갱신된다(사용자당 1개).
    resp = await client.put(SEAT_URL, json={"oauth_token": MEMBER_TOKEN}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["seat_id"] == seat_id

    assert (await client.delete(SEAT_URL, headers=auth_headers)).status_code == 204
    assert (await client.get(SEAT_URL, headers=auth_headers)).status_code == 404


@pytest.mark.asyncio
async def test_seat_requires_nonempty_token(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.put(SEAT_URL, json={"oauth_token": ""}, headers=auth_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_seat_requires_auth(client: AsyncClient) -> None:
    assert (await client.get(SEAT_URL)).status_code in (401, 403)


@pytest.mark.asyncio
async def test_seat_coexists_with_api_key(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """api_key 자격증명과 시트는 credential_type 이 달라 공존한다(기존 행 무영향)."""
    resp = await client.post(
        CREDS_URL, json={"api_key": "sk-ant-api03-existing-key"}, headers=auth_headers
    )
    assert resp.status_code == 200

    assert (
        await client.put(SEAT_URL, json={"oauth_token": OWNER_TOKEN}, headers=auth_headers)
    ).status_code == 200

    # 기존 api_key 조회 경로 무회귀.
    resp = await client.get(f"{CREDS_URL}?credential_type=api_key", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["credential_type"] == "api_key"

    rows = (await db_session.execute(select(UserAnthropicCredentials))).scalars().all()
    assert sorted(str(r.credential_type) for r in rows) == ["api_key", "oauth_token"]


# ── 머신 수령 ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_machine_seat_token_owner_fallback_roundtrip(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """배정이 없으면 소유자 시트로 폴백하고, 등록 평문과 수령 평문이 일치한다."""
    project_id = await _create_project(client, auth_headers, "시트 폴백 프로젝트")
    await client.put(SEAT_URL, json={"oauth_token": OWNER_TOKEN}, headers=auth_headers)

    resp = await client.post(SEAT_TOKEN_URL, json={"project_id": project_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token"] == OWNER_TOKEN  # Fernet round-trip
    assert body["user_id"] == str(await _user_id(db_session, "test@example.com"))


@pytest.mark.asyncio
async def test_machine_seat_token_prefers_assigned_seat(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    project_id = await _create_project(client, auth_headers, "시트 배정 프로젝트")
    await client.put(SEAT_URL, json={"oauth_token": OWNER_TOKEN}, headers=auth_headers)

    member_headers = await _register_user(client, "member@example.com")
    await client.put(SEAT_URL, json={"oauth_token": MEMBER_TOKEN}, headers=member_headers)
    member_id = str(await _user_id(db_session, "member@example.com"))

    resp = await client.put(
        f"/api/v1/projects/{project_id}/seat",
        json={"seat_user_id": member_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["seat_user_id"] == member_id

    resp = await client.post(SEAT_TOKEN_URL, json={"project_id": project_id})
    assert resp.status_code == 200
    assert resp.json()["token"] == MEMBER_TOKEN
    assert resp.json()["user_id"] == member_id

    # 해제하면 소유자 시트로 되돌아온다.
    resp = await client.put(
        f"/api/v1/projects/{project_id}/seat",
        json={"seat_user_id": None},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["seat_user_id"] is None

    resp = await client.post(SEAT_TOKEN_URL, json={"project_id": project_id})
    assert resp.json()["token"] == OWNER_TOKEN


@pytest.mark.asyncio
async def test_machine_seat_token_404_when_no_seat(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    project_id = await _create_project(client, auth_headers, "시트 없는 프로젝트")
    resp = await client.post(SEAT_TOKEN_URL, json={"project_id": project_id})
    assert resp.status_code == 404
    assert resp.json()["code"] == "SEAT_NOT_FOUND"


@pytest.mark.asyncio
async def test_machine_seat_token_404_when_project_missing(client: AsyncClient) -> None:
    resp = await client.post(SEAT_TOKEN_URL, json={"project_id": str(uuid.uuid4())})
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROJECT_NOT_FOUND"


@pytest.mark.asyncio
async def test_machine_seat_token_409_when_blocked(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """차단/소진 시트는 조용히 폴백하지 않고 409 로 거부한다."""
    project_id = await _create_project(client, auth_headers, "차단 시트 프로젝트")
    await client.put(SEAT_URL, json={"oauth_token": OWNER_TOKEN}, headers=auth_headers)

    await db_session.execute(
        update(UserAnthropicCredentials)
        .where(UserAnthropicCredentials.credential_type == "oauth_token")
        .values(seat_status="blocked")
    )
    await db_session.commit()

    resp = await client.post(SEAT_TOKEN_URL, json={"project_id": project_id})
    assert resp.status_code == 409
    assert resp.json()["code"] == "SEAT_NOT_AVAILABLE"

    # 새 토큰으로 교체하면 active 로 복구되어 다시 수령된다.
    await client.put(SEAT_URL, json={"oauth_token": OWNER_TOKEN}, headers=auth_headers)
    assert (await client.post(SEAT_TOKEN_URL, json={"project_id": project_id})).status_code == 200


# ── 배정 권한/검증 ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_seat_requires_project_ownership(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    project_id = await _create_project(client, auth_headers, "타인 프로젝트")
    other_headers = await _register_user(client, "other@example.com")
    await client.put(SEAT_URL, json={"oauth_token": MEMBER_TOKEN}, headers=other_headers)
    other_id = str(await _user_id(db_session, "other@example.com"))

    resp = await client.put(
        f"/api/v1/projects/{project_id}/seat",
        json={"seat_user_id": other_id},
        headers=other_headers,
    )
    assert resp.status_code == 404  # 소유자 스코프 밖 → 존재를 노출하지 않는다


@pytest.mark.asyncio
async def test_assign_seat_rejects_user_without_seat(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    project_id = await _create_project(client, auth_headers, "죽은 배정 방지")
    await _register_user(client, "noseat@example.com")
    noseat_id = str(await _user_id(db_session, "noseat@example.com"))

    resp = await client.put(
        f"/api/v1/projects/{project_id}/seat",
        json={"seat_user_id": noseat_id},
        headers=auth_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "SEAT_NOT_FOUND"
