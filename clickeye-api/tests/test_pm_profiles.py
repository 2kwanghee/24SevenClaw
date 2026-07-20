import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pm_profile import PMProfile
from app.models.prototype_session import Prototype, PrototypeSession
from app.models.user import User


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


async def _create_session_id(client: AsyncClient, headers: dict[str, str], db: AsyncSession) -> str:
    """테스트용 조직(API) + PrototypeSession(DB 직접 시딩)을 생성하고 session_id를 반환한다.

    위저드 프로토타입 세션 엔드포인트는 P3 에서 제거되었으므로, PM 평가/추천 회귀
    커버리지 유지를 위해 보존 모델(PrototypeSession/Prototype)에 직접 시딩한다.
    """
    org_resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "PM 테스트 회사", "size": "11-50"},
        headers=headers,
    )
    org_id = org_resp.json()["id"]

    user = (await db.execute(select(User).where(User.email == "test@example.com"))).scalar_one()

    session = PrototypeSession(
        user_id=user.id,
        organization_id=uuid.UUID(org_id),
        solution_prompt="SaaS 구독 서비스를 만들고 싶습니다",
        status="ready",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return str(session.id)


async def _create_org_and_prototype(
    client: AsyncClient, headers: dict[str, str], db: AsyncSession
) -> dict:
    """테스트용 세션 + Prototype(DB 직접 시딩)을 생성하고 첫 프로토타입을 반환한다."""
    session_id = await _create_session_id(client, headers, db)

    proto = Prototype(
        session_id=uuid.UUID(session_id),
        variant_index=0,
        title="프로토타입 A",
        description="테스트 프로토타입",
        design_pattern="dashboard",
        status="ready",
    )
    db.add(proto)
    await db.commit()
    await db.refresh(proto)
    return {"id": str(proto.id)}


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
async def test_recommend_pms(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_pm_profiles(db_session)
    prototype = await _create_org_and_prototype(client, auth_headers, db_session)

    resp = await client.post(
        "/api/v1/pm-profiles/recommend",
        json={"prototype_id": prototype["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 3
    # 점수 내림차순 정렬 확인
    scores = [item["match_score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_recommend_pms_prototype_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/pm-profiles/recommend",
        json={"prototype_id": "00000000-0000-0000-0000-000000000000"},
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

    # 세션 생성
    session_id = await _create_session_id(client, auth_headers, db_session)

    resp = await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
        json={"session_id": session_id, "rating": 4, "comment": "좋은 PM입니다"},
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
        json={
            "session_id": "00000000-0000-0000-0000-000000000001",
            "rating": 6,
        },
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
    session_id = await _create_session_id(client, auth_headers, db_session)

    # 평가 2개 등록
    for rating_val in (3, 5):
        await client.post(
            f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
            json={"session_id": session_id, "rating": rating_val},
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

    # 세션 생성 + 평가
    session_id = await _create_session_id(client, auth_headers, db_session)

    await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/ratings",
        json={"session_id": session_id, "rating": 5},
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
