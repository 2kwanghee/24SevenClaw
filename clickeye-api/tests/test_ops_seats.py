"""시트 프로비저닝 동기화 API 테스트 (CE-400).

검증 축:
  1. 성공 — active/비-active 시트가 모두(seat_status 포함) + 평문 토큰과 함께 반환.
  2. 빈 케이스 — 등록된 oauth_token 시트가 없으면 seats=[].
  3. X-Governance-Token 누락/불일치 401/403.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.crypto import encrypt
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials

_PROVISION_URL = "/api/v1/ops/seats/provision"


async def _seed_seat(
    db: AsyncSession, *, email: str, token: str, seat_status: str = "active"
) -> uuid.UUID:
    user_id = uuid.uuid4()
    seat_id = uuid.uuid4()
    db.add(
        User(
            id=user_id,
            email=email,
            password_hash="x",
            display_name="테스트",
            is_active=True,
        )
    )
    db.add(
        UserAnthropicCredentials(
            id=seat_id,
            user_id=user_id,
            encrypted_api_key=encrypt(token),
            credential_type="oauth_token",
            seat_status=seat_status,
        )
    )
    await db.commit()
    return seat_id


@pytest.mark.asyncio
async def test_provision_returns_active_and_non_active_seats(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    active_seat_id = await _seed_seat(
        db_session, email="a@example.com", token="tok-active", seat_status="active"
    )
    blocked_seat_id = await _seed_seat(
        db_session, email="b@example.com", token="tok-blocked", seat_status="blocked"
    )

    resp = await client.get(_PROVISION_URL)
    assert resp.status_code == 200, resp.text
    seats = resp.json()["seats"]
    assert len(seats) == 2

    by_id = {s["seat_id"]: s for s in seats}
    active = by_id[str(active_seat_id)]
    assert active["email"] == "a@example.com"
    assert active["seat_status"] == "active"
    assert active["token"] == "tok-active"

    blocked = by_id[str(blocked_seat_id)]
    assert blocked["email"] == "b@example.com"
    assert blocked["seat_status"] == "blocked"
    assert blocked["token"] == "tok-blocked"


@pytest.mark.asyncio
async def test_provision_empty_when_no_seats(client: AsyncClient) -> None:
    resp = await client.get(_PROVISION_URL)
    assert resp.status_code == 200, resp.text
    assert resp.json()["seats"] == []


@pytest.mark.asyncio
async def test_missing_token_401(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "governance_service_token", "ops-seats-token")
    resp = await client.get(_PROVISION_URL)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_mismatch_403(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "governance_service_token", "ops-seats-token")
    resp = await client.get(_PROVISION_URL, headers={"X-Governance-Token": "wrong"})
    assert resp.status_code == 403
