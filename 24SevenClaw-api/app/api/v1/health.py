from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis import get_redis
from app.ws.hub import agent_hub

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    # DB 연결 확인
    db_ok = False
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Redis 연결 확인
    redis_ok = False
    try:
        redis = get_redis()
        redis_ok = bool(await redis.ping())  # type: ignore[misc]
    except Exception:
        pass

    all_ok = db_ok and redis_ok
    return {
        "status": "healthy" if all_ok else "degraded",
        "version": "0.1.0",
        "db": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disconnected",
        "agents_connected": agent_hub.connected_count,
    }
