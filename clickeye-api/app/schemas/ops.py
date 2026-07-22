"""운영 패널 조회/관리 스키마 (Pydantic v2)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

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


# ---------------------------------------------------------------------------
# 관리형 환경변수 (CE-305 PR-3)
# ---------------------------------------------------------------------------


class EnvVarItem(BaseModel):
    """관리형 env 키 1건의 조회 표현.

    시크릿 값은 절대 평문으로 반환하지 않는다(masked_value 는 "***" 또는 None).
    """

    key: str = Field(description="환경변수명")
    has_value: bool = Field(description="값이 설정되어 있는지")
    is_secret: bool = Field(description="시크릿 여부(True 면 값 미반환)")
    editable: bool = Field(description="편집 가능 여부(제외 키는 False)")
    masked_value: str | None = Field(
        default=None,
        description="비시크릿은 값(절단), 시크릿은 '***'(값 있을 때), 값 없으면 None",
    )
    updated_at: datetime | None = Field(default=None, description="마지막 변경 시각")
    updated_by: UUID | None = Field(default=None, description="마지막 변경 superadmin")
    pending: bool = Field(
        default=False, description="마지막 렌더 이후 변경되어 아직 미적용인지"
    )


class EnvVarUpsert(BaseModel):
    """env 값 쓰기 요청 — value 는 write-only(응답에 포함되지 않음)."""

    value: str = Field(description="설정할 값(평문). 저장 시 Fernet 암호화됨.")


class EnvRenderRequest(BaseModel):
    """env 파일 렌더 요청. confirm=True 여야 실제 렌더 수행."""

    confirm: bool = Field(default=False, description="렌더 확정 플래그")


class EnvRenderResult(BaseModel):
    """렌더 결과 — 재생성 명령 문자열만 반환하며 docker/재생성은 실행하지 않는다."""

    rendered_path: str = Field(description="렌더된 env 파일 경로")
    rendered_at: datetime = Field(description="렌더 시각")
    applied_count: int = Field(description="파일에 기록된 관리형 키 수")
    recreate_command: str = Field(
        description="사용자가 수동 실행할 재생성 명령(백엔드는 실행하지 않음)"
    )
    services: list[str] = Field(
        default_factory=list, description="재생성 대상 관리형 서비스명"
    )
    pending: list[str] = Field(
        default_factory=list, description="렌더 후 남은 미적용 키(정상 시 빈 목록)"
    )
