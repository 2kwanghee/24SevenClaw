"""카탈로그 API 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/agents")
    assert resp.status_code == 200

    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] > 0
    assert isinstance(data["items"], list)

    agent = data["items"][0]
    assert "id" in agent
    assert "name" in agent
    assert "provider" in agent


@pytest.mark.asyncio
async def test_list_skills(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/skills")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] > 0

    skill = data["items"][0]
    assert "id" in skill
    assert "name" in skill
    assert "type" in skill


@pytest.mark.asyncio
async def test_list_platforms(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/platforms")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] > 0

    platform = data["items"][0]
    assert "id" in platform
    assert "name" in platform
    assert "config_dir" in platform
    assert "agent_file" in platform


@pytest.mark.asyncio
async def test_list_pipelines(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/catalog/pipelines")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] > 0

    pipeline = data["items"][0]
    assert "id" in pipeline
    assert "name" in pipeline
    assert "steps" in pipeline


@pytest.mark.asyncio
async def test_catalog_agents_count(client: AsyncClient) -> None:
    """total 필드가 items 길이와 일치하는지 확인."""
    resp = await client.get("/api/v1/catalog/agents")
    data = resp.json()
    assert data["total"] == len(data["items"])


@pytest.mark.asyncio
async def test_catalog_no_auth_required(client: AsyncClient) -> None:
    """카탈로그 API는 인증 없이 접근 가능."""
    for endpoint in ["agents", "skills", "platforms", "pipelines"]:
        resp = await client.get(f"/api/v1/catalog/{endpoint}")
        assert resp.status_code == 200
