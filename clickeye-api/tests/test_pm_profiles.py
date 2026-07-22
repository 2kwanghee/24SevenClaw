import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pm_profile import PMProfile


async def _seed_pm_profiles(db: AsyncSession) -> list[str]:
    """테스트용 PM 프로필을 시딩하고 ID 목록을 반환한다."""
    profiles = [
        PMProfile(
            id=uuid.uuid4(),
            name="김제품",
            slug="kim-product",
            domain="product",
            title="제품 전략 PM",
            description="제품 전략 전문 PM",
            specialties=["roadmap", "user-research", "a/b-testing"],
            personality={"leadership": 9, "communication": 8},
            is_active=True,
        ),
        PMProfile(
            id=uuid.uuid4(),
            name="이백엔드",
            slug="lee-backend",
            domain="backend",
            title="백엔드 아키텍처 PM",
            description="백엔드 아키텍처 전문 PM",
            specialties=["system-design", "api-design", "database"],
            personality={"technical": 9, "detail-oriented": 8},
            is_active=True,
        ),
        PMProfile(
            id=uuid.uuid4(),
            name="박그로스",
            slug="park-growth",
            domain="growth",
            title="성장 전략 PM",
            description="성장 전략 전문 PM",
            specialties=["analytics", "marketing", "conversion"],
            personality={"data-driven": 9, "creative": 7},
            is_active=True,
        ),
    ]
    for p in profiles:
        db.add(p)
    await db.commit()

    ids: list[str] = []
    for p in profiles:
        await db.refresh(p)
        ids.append(str(p.id))
    return ids


@pytest.mark.asyncio
async def test_list_profiles_empty(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get("/api/v1/pm-profiles/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_profiles(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_pm_profiles(db_session)

    resp = await client.get("/api/v1/pm-profiles/", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3


@pytest.mark.asyncio
async def test_list_profiles_filter_domain(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_pm_profiles(db_session)

    resp = await client.get("/api/v1/pm-profiles/?domain=product", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["domain"] == "product"


@pytest.mark.asyncio
async def test_get_profile(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    resp = await client.get(f"/api/v1/pm-profiles/{pm_ids[0]}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "김제품"


@pytest.mark.asyncio
async def test_get_profile_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get(
        "/api/v1/pm-profiles/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_rate_pm(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    # PM 평가는 pm_profile + user 스코프 — 세션 개념 없이 동작한다.
    resp = await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
        json={"rating": 4, "comment": "좋은 PM입니다"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["rating"] == 4
    assert body["comment"] == "좋은 PM입니다"


@pytest.mark.asyncio
async def test_rate_pm_invalid_score(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    resp = await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
        json={"rating": 6},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_ratings(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    # 평가 2개 등록
    for rating_val in (3, 5):
        await client.post(
            f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
            json={"rating": rating_val},
            headers=auth_headers,
        )

    resp = await client.get(
        f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_get_metrics(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
        json={"rating": 5},
        headers=auth_headers,
    )

    resp = await client.get(f"/api/v1/pm-profiles/{pm_ids[0]}/metrics", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_ratings"] == 1
    assert body["avg_rating"] == 5.0


@pytest.mark.asyncio
async def test_get_metrics_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    resp = await client.get(
        "/api/v1/pm-profiles/00000000-0000-0000-0000-000000000000/metrics",
        headers=auth_headers,
    )
    assert resp.status_code == 404
