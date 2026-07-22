"""asyncio TCP 포트 프로브.

`settings.ops_port_targets` 의 각 대상에 대해 TCP 연결을 시도해 도달성/지연을 측정한다.
대상 형식: "host:port" 또는 "service=host:port" (service 생략 시 "host:port" 를 이름으로 사용).
"""

from __future__ import annotations

import asyncio
import time

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROBE_TIMEOUT = 2.0


def _parse_target(target: str) -> tuple[str, str, int] | None:
    """대상 문자열을 (service, host, port) 로 파싱. 형식 오류 시 None."""
    raw = target.strip()
    if not raw:
        return None
    if "=" in raw:
        service, hostport = raw.split("=", 1)
        service = service.strip()
    else:
        hostport = raw
        service = raw
    hostport = hostport.strip()
    if ":" not in hostport:
        return None
    host, _, port_str = hostport.rpartition(":")
    host = host.strip()
    if not host:
        return None
    try:
        port = int(port_str.strip())
    except ValueError:
        return None
    # 범위 밖 포트(오타/음수)는 skip — 해당 타겟만 제외하고 나머지는 정상 프로브(부분 degrade).
    if not (0 <= port <= 65535):
        logger.info("ops_port_target_out_of_range", target=raw, port=port)
        return None
    return service, host, port


async def _probe_one(service: str, host: str, port: int) -> dict[str, object]:
    """단일 대상 TCP 프로브."""
    start = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=_PROBE_TIMEOUT
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        # close() 로 정리만 스케줄한다. wait_closed() 는 피어가 half-open 을 유지하면
        # 무한 대기할 수 있어 프로브에서는 사용하지 않는다.
        writer.close()
        return {
            "service": service,
            "host": host,
            "port": port,
            "reachable": True,
            "latency_ms": round(latency_ms, 2),
        }
    except (TimeoutError, OSError, OverflowError, ValueError) as exc:
        # OverflowError/ValueError: 범위 밖 포트가 파싱 단계를 우회한 경우의 방어적 이중 처리.
        logger.info("ops_port_unreachable", service=service, host=host, port=port, error=str(exc))
        return {
            "service": service,
            "host": host,
            "port": port,
            "reachable": False,
            "latency_ms": None,
        }


async def probe_ports() -> list[dict[str, object]]:
    """설정된 모든 포트 대상을 병렬로 프로브한 결과 목록 반환."""
    parsed = [p for t in settings.ops_port_targets if (p := _parse_target(t)) is not None]
    if not parsed:
        return []
    results = await asyncio.gather(*(_probe_one(svc, host, port) for svc, host, port in parsed))
    return list(results)
