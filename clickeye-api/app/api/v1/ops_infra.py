"""운영 패널 읽기 전용 인프라 조회 endpoint (superadmin 전용).

feature flag `feature_ops_panel` OFF 시 모든 endpoint 404.
어떤 endpoint 도 쓰기(POST 등)를 수행하지 않으며, 상태 조회만 제공한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import require_ops_feature, require_superadmin
from app.schemas.ops import ContainerStatus, PortStatus
from app.services.ops import docker_client, port_probe

router = APIRouter(
    prefix="/admin/ops",
    tags=["ops"],
    dependencies=[Depends(require_ops_feature), Depends(require_superadmin)],
)


@router.get("/containers", response_model=list[ContainerStatus])
async def list_containers() -> list[ContainerStatus]:
    """read-only dockerproxy 를 통한 컨테이너 상태 목록."""
    raw = await docker_client.list_containers()
    return [ContainerStatus(**item) for item in raw]


@router.get("/ports", response_model=list[PortStatus])
async def list_ports() -> list[PortStatus]:
    """설정된 포트 대상들의 TCP 도달성 상태."""
    raw = await port_probe.probe_ports()
    return [PortStatus(**item) for item in raw]
