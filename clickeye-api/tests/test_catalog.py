"""카탈로그 API 테스트.

agents/skills 는 DB SSOT(registry 모델)이므로 테스트 카탈로그 시드가 필요하다 —
conftest.seeded_catalog(tests/catalog_test_data.seed_catalog_db)를 모듈 전체에
autouse 로 주입한다(프로덕션 코드 무변경). platforms/pipelines 는 JSON 파일 기반.
"""

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
async def _seed_registry(seeded_catalog: None) -> None:
    """공개 agents 7 / skills 6 시드 — DB SSOT 카탈로그 엔드포인트 전제 데이터."""
    return


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/agents")
    assert resp.status_code == 200

    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 7
    assert isinstance(data["items"], list)

    agent = data["items"][0]
    assert "id" in agent
    assert "label" in agent
    assert "description" in agent


@pytest.mark.asyncio
async def test_list_skills(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/skills")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 6

    skill = data["items"][0]
    assert "id" in skill
    assert "label" in skill
    assert "description" in skill


@pytest.mark.asyncio
async def test_list_platforms(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/platforms")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] > 0

    platform = data["items"][0]
    assert "id" in platform
    assert "name" in platform


@pytest.mark.asyncio
async def test_list_pipelines(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/pipelines")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] > 0

    pipeline = data["items"][0]
    assert "id" in pipeline
    assert "name" in pipeline


@pytest.mark.asyncio
async def test_catalog_agents_count(client: AsyncClient) -> None:
    """total 필드가 items 길이와 일치하는지 확인."""
    resp = await client.get("/api/v1/catalog/agents")
    data = resp.json()
    assert data["total"] == len(data["items"])


@pytest.mark.asyncio
async def test_catalog_agents_slugs(client: AsyncClient) -> None:
    """7개 harness 역할 에이전트 slug 검증."""
    resp = await client.get("/api/v1/catalog/agents")
    data = resp.json()
    ids = {item["id"] for item in data["items"]}
    expected = {"harness", "architect", "frontend", "backend", "qa", "devops", "security"}
    assert ids == expected


@pytest.mark.asyncio
async def test_catalog_skills_slugs(client: AsyncClient) -> None:
    """6개 공개 스킬 slug 검증 — 테스트 카탈로그 계약(catalog_test_data._SKILLS).

    (구 통합 스킬 세트 telegram/github/slack/jira 는 폐기 — jira 는 031 마이그레이션
    에서 비공개 처리. 현 계약은 개발 워크플로 스킬 중심.)
    """
    resp = await client.get("/api/v1/catalog/skills")
    data = resp.json()
    ids = {item["id"] for item in data["items"]}
    expected = {
        "linear",
        "notion",
        "tdd-smart-coding",
        "harness-gate",
        "ai-critique",
        "ralph-loop",
    }
    assert ids == expected


@pytest.mark.asyncio
async def test_catalog_no_auth_required(client: AsyncClient) -> None:
    """카탈로그 API는 인증 없이 접근 가능."""
    for endpoint in ["agents", "skills", "platforms", "pipelines"]:
        resp = await client.get(f"/api/v1/catalog/{endpoint}")
        assert resp.status_code == 200
