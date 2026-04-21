"""Rate Limiting 미들웨어 테스트."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_bypassed_when_redis_none(client: AsyncClient) -> None:
    """Redis 미연결 시 요청이 차단되지 않음."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client: AsyncClient) -> None:
    """Redis 연결 시 응답에 Rate Limit 헤더 포함."""
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.expire = AsyncMock()
    mock_redis.ttl = AsyncMock(return_value=60)

    with patch("app.core.rate_limit.redis_client", mock_redis):
        resp = await client.get("/api/v1/health")

    # 헬스체크는 Rate Limit 제외
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_auth_endpoint_stricter(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """인증 엔드포인트는 차등 제한 (10/60초) 적용."""
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=5)
    mock_redis.expire = AsyncMock()
    mock_redis.ttl = AsyncMock(return_value=55)

    with patch("app.core.rate_limit.redis_client", mock_redis):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.headers.get("x-ratelimit-limit") == "10"
    assert resp.headers.get("x-ratelimit-remaining") == "5"
    assert resp.headers.get("x-ratelimit-reset") == "55"


@pytest.mark.asyncio
async def test_rate_limit_default_endpoint(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """일반 엔드포인트는 기본 제한 (100/60초) 적용."""
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=5)
    mock_redis.expire = AsyncMock()
    mock_redis.ttl = AsyncMock(return_value=55)

    with patch("app.core.rate_limit.redis_client", mock_redis):
        resp = await client.get("/api/v1/catalog/agents", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.headers.get("x-ratelimit-limit") == "100"
    assert resp.headers.get("x-ratelimit-remaining") == "95"
    assert resp.headers.get("x-ratelimit-reset") == "55"


@pytest.mark.asyncio
async def test_rate_limit_exceeded(client: AsyncClient) -> None:
    """Rate Limit 초과 시 429 응답."""
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=101)
    mock_redis.expire = AsyncMock()
    mock_redis.ttl = AsyncMock(return_value=30)

    with patch("app.core.rate_limit.redis_client", mock_redis):
        resp = await client.get("/api/v1/catalog/agents")

    assert resp.status_code == 429
    data = resp.json()
    assert data["code"] == "RATE_LIMIT_EXCEEDED"
    assert resp.headers.get("retry-after") == "30"
    assert resp.headers.get("x-ratelimit-remaining") == "0"


@pytest.mark.asyncio
async def test_rate_limit_auth_exceeded(client: AsyncClient) -> None:
    """인증 엔드포인트 Rate Limit 초과 시 429 응답."""
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(return_value=11)
    mock_redis.expire = AsyncMock()
    mock_redis.ttl = AsyncMock(return_value=45)

    with patch("app.core.rate_limit.redis_client", mock_redis):
        resp = await client.get("/api/v1/auth/me")

    assert resp.status_code == 429
    data = resp.json()
    assert data["code"] == "RATE_LIMIT_EXCEEDED"
    assert resp.headers.get("x-ratelimit-limit") == "10"


@pytest.mark.asyncio
async def test_rate_limit_redis_error_passthrough(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Redis 오류 시 요청을 차단하지 않고 통과."""
    mock_redis = AsyncMock()
    mock_redis.incr = AsyncMock(side_effect=Exception("Redis connection lost"))

    with patch("app.core.rate_limit.redis_client", mock_redis):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)

    # Redis 장애여도 요청은 통과
    assert resp.status_code == 200
