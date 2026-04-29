from redis.asyncio import Redis

from app.config import settings

redis_client: Redis | None = None


async def init_redis() -> None:
    """Redis 연결 풀 초기화."""
    global redis_client  # noqa: PLW0603
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    """Redis 연결 풀 종료."""
    global redis_client  # noqa: PLW0603
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


def get_redis() -> Redis:
    """Redis 클라이언트 의존성."""
    if redis_client is None:
        msg = "Redis가 초기화되지 않았습니다"
        raise RuntimeError(msg)
    return redis_client
