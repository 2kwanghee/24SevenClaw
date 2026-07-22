"""운영 패널 읽기 전용 조회 스키마 (Pydantic v2)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContainerStatus(BaseModel):
    """dockerproxy `GET /containers/json` 정규화 결과.

    시크릿 노출 방지를 위해 환경변수/명령은 절대 포함하지 않는다.
    """

    name: str = Field(description="컨테이너 이름")
    image: str = Field(description="이미지 태그")
    state: str = Field(description="상태 요약 (running/exited 등)")
    status: str = Field(description="상세 상태 문자열 (예: Up 2 hours)")
    health: str | None = Field(
        default=None, description="헬스체크 상태 (healthy/unhealthy/starting)"
    )
    ports: list[str] = Field(default_factory=list, description="포트 매핑 문자열 목록")
    created: int = Field(default=0, description="생성 시각 (unix epoch)")


class PortStatus(BaseModel):
    """`ops_port_targets` 각 대상에 대한 TCP 도달성 프로브 결과."""

    service: str = Field(description="서비스/대상 논리 이름")
    host: str = Field(description="프로브 호스트")
    port: int = Field(description="프로브 포트")
    reachable: bool = Field(description="TCP 연결 성공 여부")
    latency_ms: float | None = Field(default=None, description="연결 지연 (ms), 실패 시 None")
