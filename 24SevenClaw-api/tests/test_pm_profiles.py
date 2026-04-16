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
            specialty="product",
            description="제품 전략 전문 PM",
            skills=["roadmap", "user-research", "a/b-testing"],
            experience_areas=["saas", "fintech"],
            personality_traits={"leadership": 9, "communication": 8},
            is_active=True,
        ),
        PMProfile(
            id=uuid.uuid4(),
            name="이백엔드",
            slug="lee-backend",
            specialty="backend",
            description="백엔드 아키텍처 전문 PM",
            skills=["system-design", "api-design", "database"],
            experience_areas=["rest-api", "microservices"],
            personality_traits={"technical": 9, "detail-oriented": 8},
            is_active=True,
        ),
        PMProfile(
            id=uuid.uuid4(),
            name="박그로스",
            slug="park-growth",
            specialty="growth",
            description="성장 전략 전문 PM",
            skills=["analytics", "marketing", "conversion"],
            experience_areas=["saas", "marketplace"],
            personality_traits={"data-driven": 9, "creative": 7},
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


async def _create_org_and_prototype(
    client: AsyncClient, headers: dict[str, str]
) -> dict:
    """테스트용 조직 + 세션 + 프로토타입을 생성하고 첫 프로토타입을 반환한다."""
    # 조직 생성
    org_resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "PM 테스트 회사", "size": "11-50"},
        headers=headers,
    )
    org_id = org_resp.json()["id"]

    # 세션 생성
    session_resp = await client.post(
        "/api/v1/prototype-sessions/",
        json={
            "organization_id": org_id,
            "user_input": {
                "company_name": "PM 테스트 회사",
                "description": "SaaS 구독 서비스",
                "business_type": "saas",
            },
        },
        headers=headers,
    )
    session_id = session_resp.json()["id"]

    # 프로토타입 생성
    gen_resp = await client.post(
        f"/api/v1/prototype-sessions/{session_id}/generate",
        headers=headers,
    )
    return gen_resp.json()[0]


@pytest.mark.asyncio
async def test_list_profiles_empty(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
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
async def test_list_profiles_filter_specialty(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    await _seed_pm_profiles(db_session)

    resp = await client.get(
        "/api/v1/pm-profiles/?specialty=product", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["specialty"] == "product"


@pytest.mark.asyncio
async def test_get_profile(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    resp = await client.get(
        f"/api/v1/pm-profiles/{pm_ids[0]}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "김제품"


@pytest.mark.asyncio
async def test_get_profile_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
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
    prototype = await _create_org_and_prototype(client, auth_headers)

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

    # 프로젝트 생성
    project_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "평가 테스트 프로젝트"},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/rate",
        json={"project_id": project_id, "score": 4, "comment": "좋은 PM입니다"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == 4
    assert body["comment"] == "좋은 PM입니다"


@pytest.mark.asyncio
async def test_rate_pm_invalid_score(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    resp = await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/rate",
        json={
            "project_id": "00000000-0000-0000-0000-000000000000",
            "score": 6,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_metrics(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    pm_ids = await _seed_pm_profiles(db_session)

    # 프로젝트 생성 + 평가
    project_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "메트릭 테스트"},
        headers=auth_headers,
    )
    project_id = project_resp.json()["id"]

    await client.post(
        f"/api/v1/pm-profiles/{pm_ids[0]}/rate",
        json={"project_id": project_id, "score": 5},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/pm-profiles/{pm_ids[0]}/metrics", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_projects"] == 1
    assert body["avg_rating"] == 5.0


@pytest.mark.asyncio
async def test_get_metrics_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get(
        "/api/v1/pm-profiles/00000000-0000-0000-0000-000000000000/metrics",
        headers=auth_headers,
    )
    assert resp.status_code == 404
