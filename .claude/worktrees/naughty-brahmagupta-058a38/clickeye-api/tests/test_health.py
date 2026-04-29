"""health 엔드포인트 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200

    data = resp.json()
    assert "status" in data
    assert "version" in data
    assert "db" in data
    assert "redis" in data
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_status_field(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    data = resp.json()
    assert data["status"] in ("healthy", "degraded")
