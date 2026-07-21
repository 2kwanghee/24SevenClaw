"""read-only dockerproxy 클라이언트.

dockerproxy(tecnativa/docker-socket-proxy, POST=0)에 httpx GET 만 수행한다.
- `list_containers`: `GET /containers/json?all=1` 를 안전 필드만 정규화.
- `inspect_container`: `GET /containers/{id}/json` 응답을 **allowlist 로 정규화**하여
  명시적으로 선별한 안전 필드만 반환한다. Env/Cmd/Args/Path/Entrypoint/Labels/
  Healthcheck/HostConfig(Binds·Mounts)/NetworkSettings 상세 등 시크릿·명령줄·바인드
  경로는 절대 포함하지 않는다(denylist 가 아닌 allowlist 로 유출 여지 제거).

프록시 미가용/타임아웃 시 AppError(503)로 명확히 degrade 한다.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

from app.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

# 프록시는 내부망 전용이므로 짧은 타임아웃으로 빠르게 degrade.
_TIMEOUT = 5.0

# 컨테이너 식별자 형식(이름/short·full 해시). 경로 주입 방지용 화이트리스트 패턴.
_CONTAINER_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


async def _get(path: str) -> Any:
    """dockerproxy 에 GET 요청. 실패 시 AppError(503)."""
    try:
        async with httpx.AsyncClient(base_url=settings.docker_proxy_url, timeout=_TIMEOUT) as cli:
            resp = await cli.get(path)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.warning("ops_docker_unavailable", path=path, error=str(exc))
        raise AppError(
            "OPS_DOCKER_UNAVAILABLE",
            "Docker 상태 프록시에 연결할 수 없습니다. 프록시 가용성을 확인하세요.",
            503,
        ) from exc


def _format_ports(raw_ports: list[dict[str, Any]] | None) -> list[str]:
    """docker Ports 배열을 사람이 읽는 문자열 목록으로 변환."""
    if not raw_ports:
        return []
    formatted: list[str] = []
    for p in raw_ports:
        proto = p.get("Type", "tcp")
        private = p.get("PrivatePort")
        public = p.get("PublicPort")
        ip = p.get("IP")
        if public is not None:
            prefix = f"{ip}:" if ip else ""
            formatted.append(f"{prefix}{public}->{private}/{proto}")
        else:
            formatted.append(f"{private}/{proto}")
    return formatted


def _parse_health(status: str) -> str | None:
    """상태 문자열에서 헬스체크 상태를 추출 (예: 'Up 2 hours (healthy)')."""
    low = status.lower()
    if "(healthy)" in low:
        return "healthy"
    if "(unhealthy)" in low:
        return "unhealthy"
    if "health: starting" in low or "(starting)" in low:
        return "starting"
    return None


def _normalize_container(raw: dict[str, Any]) -> dict[str, Any]:
    """`GET /containers/json` 항목을 안전한 요약 dict 로 정규화.

    시크릿(환경변수 등)은 이 응답에 포함되지 않으며, 명시적으로 선별한 필드만 반환한다.
    """
    names = raw.get("Names") or []
    name = names[0].lstrip("/") if names else raw.get("Id", "")[:12]
    status = raw.get("Status", "")
    return {
        "name": name,
        "image": raw.get("Image", ""),
        "state": raw.get("State", ""),
        "status": status,
        "health": _parse_health(status),
        "ports": _format_ports(raw.get("Ports")),
        "created": int(raw.get("Created", 0) or 0),
    }


def _ports_from_network_settings(network_settings: Any) -> list[str]:
    """inspect 의 NetworkSettings.Ports 를 IP 제외한 포트 매핑 문자열로 변환."""
    if not isinstance(network_settings, dict):
        return []
    ports = network_settings.get("Ports")
    if not isinstance(ports, dict):
        return []
    out: list[str] = []
    for container_port, bindings in ports.items():
        if isinstance(bindings, list) and bindings:
            for b in bindings:
                host_port = b.get("HostPort") if isinstance(b, dict) else None
                out.append(f"{container_port}->{host_port}" if host_port else str(container_port))
        else:
            out.append(str(container_port))
    return out


def _normalize_inspect(raw: dict[str, Any]) -> dict[str, Any]:
    """inspect 응답을 allowlist 로 정규화 — 안전 필드만 선별 반환.

    반환 필드: id, name, image, state, status, health, created, restart_count, ports.
    Env/Cmd/Args/Path/Entrypoint/Labels/Healthcheck/HostConfig/Mounts 등 민감 필드는
    의도적으로 제외한다(신규 필드가 프록시 응답에 생겨도 자동 노출되지 않음).
    """
    config_raw = raw.get("Config")
    config = config_raw if isinstance(config_raw, dict) else {}
    state_raw = raw.get("State")
    state = state_raw if isinstance(state_raw, dict) else {}
    health_raw = state.get("Health")
    health = health_raw if isinstance(health_raw, dict) else {}
    name = raw.get("Name", "")
    return {
        "id": str(raw.get("Id", ""))[:12],
        "name": name.lstrip("/") if isinstance(name, str) else "",
        "image": config.get("Image") or raw.get("Image", ""),
        "state": state.get("Status", ""),
        "status": state.get("Status", ""),
        "health": health.get("Status"),
        "created": raw.get("Created", ""),
        "restart_count": raw.get("RestartCount", 0),
        "ports": _ports_from_network_settings(raw.get("NetworkSettings")),
    }


async def list_containers() -> list[dict[str, Any]]:
    """모든 컨테이너의 정규화된 상태 목록 반환."""
    data = await _get("/containers/json?all=1")
    if not isinstance(data, list):
        return []
    return [_normalize_container(c) for c in data if isinstance(c, dict)]


async def inspect_container(container_id: str) -> dict[str, Any]:
    """단일 컨테이너 inspect 결과 (allowlist 정규화된 안전 필드만).

    `container_id` 는 이름/해시 형식(`^[a-zA-Z0-9_.-]+$`)만 허용 — 경로 주입 방지.
    """
    if not _CONTAINER_ID_RE.match(container_id):
        raise AppError(
            "OPS_INVALID_CONTAINER_ID",
            "유효하지 않은 컨테이너 식별자입니다.",
            400,
        )
    raw = await _get(f"/containers/{container_id}/json")
    if not isinstance(raw, dict):
        return {}
    return _normalize_inspect(raw)
