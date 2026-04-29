"""Redis 기반 Rate Limiting 미들웨어."""

from __future__ import annotations

import ipaddress

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.config import settings
from app.core.logging import get_logger
from app.redis import redis_client

logger = get_logger(__name__)

# Rate limit 면제 경로
_EXEMPT_PATHS = frozenset({"/api/v1/health"})

# 인증 경로 접두사 (차등 제한 적용)
_AUTH_PREFIX = "/api/v1/auth"


def _get_client_ip(request: Request) -> str:
    """X-Forwarded-For 헤더에서 클라이언트 IP 추출. 유효하지 않으면 직접 연결 IP 사용."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # 첫 번째 IP가 원래 클라이언트 (프록시 체인에서 가장 좌측)
        candidate = forwarded.split(",")[0].strip()
        try:
            ipaddress.ip_address(candidate)
            return candidate
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def _get_rate_limit(path: str) -> tuple[int, int]:
    """경로에 따른 (요청 수, 윈도우 초) 반환."""
    if path.startswith(_AUTH_PREFIX):
        return settings.rate_limit_auth_requests, settings.rate_limit_auth_window
    return settings.rate_limit_default_requests, settings.rate_limit_default_window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """IP 기반 슬라이딩 윈도우 Rate Limiter (엔드포인트별 차등)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path in _EXEMPT_PATHS:
            return await call_next(request)

        if redis_client is None:
            return await call_next(request)

        client_ip = _get_client_ip(request)
        max_requests, window = _get_rate_limit(path)

        # 인증 경로는 별도 키로 분리
        if path.startswith(_AUTH_PREFIX):
            key = f"rate_limit:auth:{client_ip}"
        else:
            key = f"rate_limit:{client_ip}"

        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, window)

            ttl = await redis_client.ttl(key)

            if current > max_requests:
                logger.warning(
                    "rate_limit_exceeded",
                    client_ip=client_ip,
                    path=path,
                    count=current,
                    limit=max_requests,
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "요청이 너무 많습니다. 잠시 후 다시 시도해주세요.",
                        "code": "RATE_LIMIT_EXCEEDED",
                    },
                    headers={
                        "Retry-After": str(ttl),
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(ttl),
                    },
                )

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, max_requests - current)
            )
            response.headers["X-RateLimit-Reset"] = str(ttl)
            return response

        except Exception:
            # Redis 장애 시 요청을 차단하지 않음
            logger.exception("rate_limit_error", client_ip=client_ip)
            return await call_next(request)
