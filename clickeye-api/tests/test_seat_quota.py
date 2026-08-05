"""시트 잔량 스냅샷 API 테스트 (CE-387).

검증 축:
  1. 배치 수신(POST /snapshots) — 계정 2개(각 five_hour+seven_day+scoped 1개)
     → 6행 생성.
  2. 최신 조회(GET /latest) — 계정별 최신 스냅샷 조회.
  3. fiveHour.resetsAt 부재 케이스 파싱 성공.
  4. 이메일 미매칭 시 seat_id=NULL 케이스.
  5. X-Governance-Token 누락/불일치 401/403.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.seat_quota_snapshot import SeatQuotaSnapshot
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials

_SNAPSHOTS_URL = "/api/v1/ops/seat-quota/snapshots"
_LATEST_URL = "/api/v1/ops/seat-quota/latest"


def _account(email: str, *, org_uuid: str = "org-1", include_reset: bool = True) -> dict:
    five_hour: dict = {"pct": 12.5}
    if include_reset:
        five_hour["resetsAt"] = "2026-08-05T05:00:00Z"
    return {
        "number": 1,
        "email": email,
        "organizationName": "Org A",
        "organizationUuid": org_uuid,
        "active": True,
        "usageStatus": "ok",
        "usageFetchedAt": "2026-08-05T00:00:00Z",
        "usage": {
            "fiveHour": five_hour,
            "sevenDay": {
                "pct": 30.0,
                "resetsAt": "2026-08-10T00:00:00Z",
                "expectedPct": 28.0,
                "aheadOfPace": True,
                "willLastToReset": True,
            },
            "scoped": [
                {
                    "name": "claude-sonnet-5",
                    "pct": 5.0,
                    "resetsAt": "2026-08-06T00:00:00Z",
                    "expectedPct": 4.0,
                    "aheadOfPace": True,
                    "willLastToReset": True,
                }
            ],
        },
    }


async def _seed_user_with_seat(db: AsyncSession, email: str) -> uuid.UUID:
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
            encrypted_api_key="enc",
            credential_type="oauth_token",
        )
    )
    await db.commit()
    return seat_id


# ── 배치 수신 ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_batch_creates_six_rows_for_two_accounts(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    seat_id = await _seed_user_with_seat(db_session, "a@example.com")

    body = {
        "accounts": [
            _account("a@example.com"),
            _account("b@example.com", org_uuid="org-2"),
        ]
    }
    resp = await client.post(_SNAPSHOTS_URL, json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["rows_created"] == 6
    assert data["accounts_processed"] == 2
    assert data["accounts_skipped"] == 0

    rows = (await db_session.execute(select(SeatQuotaSnapshot))).scalars().all()
    assert len(rows) == 6

    a_rows = [r for r in rows if r.account_email == "a@example.com"]
    assert len(a_rows) == 3
    assert all(r.seat_id == seat_id for r in a_rows)

    b_rows = [r for r in rows if r.account_email == "b@example.com"]
    assert len(b_rows) == 3
    assert all(r.seat_id is None for r in b_rows)  # 이메일 미매칭 → NULL(행은 유지)


@pytest.mark.asyncio
async def test_batch_accepts_missing_five_hour_resets_at(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    body = {"accounts": [_account("c@example.com", include_reset=False)]}
    resp = await client.post(_SNAPSHOTS_URL, json=body)
    assert resp.status_code == 200, resp.text
    assert resp.json()["rows_created"] == 3

    row = (
        await db_session.execute(
            select(SeatQuotaSnapshot).where(
                SeatQuotaSnapshot.account_email == "c@example.com",
                SeatQuotaSnapshot.window == "five_hour",
            )
        )
    ).scalar_one()
    assert row.resets_at is None


@pytest.mark.asyncio
async def test_unmatched_email_sets_seat_id_null(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    resp = await client.post(_SNAPSHOTS_URL, json={"accounts": [_account("nomatch@example.com")]})
    assert resp.status_code == 200, resp.text

    rows = (
        (
            await db_session.execute(
                select(SeatQuotaSnapshot).where(
                    SeatQuotaSnapshot.account_email == "nomatch@example.com"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 3
    assert all(r.seat_id is None for r in rows)


# ── 최신 조회 ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_latest_returns_per_account_window_scope(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    body = {
        "accounts": [
            _account("a@example.com"),
            _account("b@example.com", org_uuid="org-2"),
        ]
    }
    resp = await client.post(_SNAPSHOTS_URL, json=body)
    assert resp.status_code == 200, resp.text

    resp = await client.get(_LATEST_URL)
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 6  # 2 계정 × 3 window(five_hour/seven_day/scoped)

    by_key = {(i["account_email"], i["window"], i["scope_name"]): i for i in items}
    assert ("a@example.com", "five_hour", None) in by_key
    assert ("a@example.com", "seven_day", None) in by_key
    assert ("a@example.com", "scoped", "claude-sonnet-5") in by_key
    assert ("b@example.com", "five_hour", None) in by_key


@pytest.mark.asyncio
async def test_latest_picks_most_recent_snapshot(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """동일 계정에 두 번 스냅샷을 보내면 latest 는 최신 captured_at 행만 반환한다."""
    first = _account("a@example.com")
    resp = await client.post(_SNAPSHOTS_URL, json={"accounts": [first]})
    assert resp.status_code == 200

    second = _account("a@example.com")
    second["usage"]["fiveHour"]["pct"] = 99.9
    resp = await client.post(_SNAPSHOTS_URL, json={"accounts": [second]})
    assert resp.status_code == 200

    resp = await client.get(_LATEST_URL)
    items = resp.json()["items"]
    five_hour_items = [
        i for i in items if i["account_email"] == "a@example.com" and i["window"] == "five_hour"
    ]
    assert len(five_hour_items) == 1
    assert float(five_hour_items[0]["pct"]) == 99.9


# ── 거버넌스 토큰 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_missing_token_401(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "governance_service_token", "seat-quota-token")
    resp = await client.post(_SNAPSHOTS_URL, json={"accounts": []})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_mismatch_403(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "governance_service_token", "seat-quota-token")
    resp = await client.post(
        _SNAPSHOTS_URL,
        json={"accounts": []},
        headers={"X-Governance-Token": "wrong"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_latest_requires_token(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "governance_service_token", "seat-quota-token")
    resp = await client.get(_LATEST_URL)
    assert resp.status_code == 401
