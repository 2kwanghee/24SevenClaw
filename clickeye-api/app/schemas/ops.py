"""운영 패널 조회/관리 스키마 (Pydantic v2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
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
    pending: bool = Field(default=False, description="마지막 렌더 이후 변경되어 아직 미적용인지")


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
    services: list[str] = Field(default_factory=list, description="재생성 대상 관리형 서비스명")
    pending: list[str] = Field(
        default_factory=list, description="렌더 후 남은 미적용 키(정상 시 빈 목록)"
    )


# ---------------------------------------------------------------------------
# webhook 수신부 env (CE-421, WEBHOOK_SECRET_MAP 렌더)
# ---------------------------------------------------------------------------


class WebhookEnvProjectItem(BaseModel):
    """WEBHOOK_SECRET_MAP 후보 1건 — 시크릿 평문은 절대 포함하지 않는다."""

    project_id: UUID = Field(description="프로젝트 ID")
    project_name: str = Field(description="프로젝트명")
    team_id: str = Field(description="Linear 팀 ID(MAP 의 좌변)")
    has_secret: bool = Field(description="webhook signing secret 보유 여부(값은 미반환)")


class WebhookEnvStatus(BaseModel):
    """렌더 대상 파일의 현재 상태 + MAP 후보 목록."""

    rendered_path: str = Field(description="렌더 대상 webhook.env 경로")
    file_exists: bool = Field(description="파일 존재 여부")
    map_line_present: bool = Field(description="WEBHOOK_SECRET_MAP= 라인 존재 여부")
    legacy_present: bool = Field(
        description="값이 채워진 WEBHOOK_SECRET(S) 라인 존재 여부(그 시크릿은 팀 검사 미적용)"
    )
    projects: list[WebhookEnvProjectItem] = Field(
        default_factory=list, description="Linear 자격증명이 등록된 프로젝트 목록"
    )


class WebhookEnvSkippedItem(BaseModel):
    """파서 파괴 문자로 MAP 에서 제외된 항목(fail-closed) — 시크릿 값 미포함."""

    project_id: UUID = Field(description="제외된 프로젝트 ID")
    project_name: str = Field(description="제외된 프로젝트명")
    team_id: str = Field(description="Linear 팀 ID")
    reason: str = Field(description="제외 사유(시크릿 값은 포함하지 않음)")


class WebhookEnvRenderResult(BaseModel):
    """webhook.env 렌더 결과 — MAP 라인만 교체하며 docker/재기동은 실행하지 않는다."""

    rendered_path: str = Field(description="렌더된 webhook.env 경로")
    rendered_at: datetime = Field(description="렌더 시각")
    entry_count: int = Field(description="MAP 에 기록된 teamId=secret 항목 수")
    dropped_line_count: int = Field(
        default=0,
        description="보존 대상이 아니어서 제거한 비정상 라인 수(제어문자 포함 등). 내용은 미반환",
    )
    skipped: list[WebhookEnvSkippedItem] = Field(
        default_factory=list, description="파서 파괴 문자로 제외된 항목"
    )
    legacy_present: bool = Field(
        description="값이 채워진 WEBHOOK_SECRET(S) 라인이 남아 있는지(팀 검사 미적용 경고)"
    )
    restart_command: str = Field(
        description="사용자가 수동 실행할 webhook 재생성 명령(백엔드는 실행하지 않음)"
    )


# ---------------------------------------------------------------------------
# 화이트리스트 테이블 CRUD (CE-305 PR-4)
# ---------------------------------------------------------------------------


class TableInfo(BaseModel):
    """화이트리스트 테이블 1건의 목록 표현."""

    key: str = Field(description="테이블 논리 키")
    label: str = Field(description="사람이 읽는 라벨")
    ops: list[str] = Field(description="허용 연산 목록 (read/create/update/delete)")
    row_count: int | None = Field(default=None, description="행 수(집계 실패 시 None)")


class TableColumnSchema(BaseModel):
    """동적 폼 렌더용 컬럼 디스크립터."""

    name: str = Field(description="컬럼명")
    type: str = Field(description="논리 타입 (str/int/float/bool/uuid/datetime/json/enum)")
    required: bool = Field(description="create 시 필수 여부")
    editable: bool = Field(description="update 시 수정 가능 여부")
    creatable: bool = Field(description="create 시 설정 가능 여부(자동생성 PK/타임스탬프는 False)")
    sensitive: bool = Field(description="시크릿 여부(조회/감사에서 마스킹)")
    max_length: int | None = Field(default=None, description="문자열 최대 길이")
    enum: list[str] | None = Field(default=None, description="enum 허용값 목록")


class TableSchema(BaseModel):
    """테이블 스키마(컬럼 디스크립터 집합) 응답."""

    key: str = Field(description="테이블 논리 키")
    label: str = Field(description="사람이 읽는 라벨")
    pk_column: str = Field(description="기본키 컬럼명")
    allowed_ops: list[str] = Field(description="허용 연산 목록")
    columns: list[TableColumnSchema] = Field(description="컬럼 디스크립터 목록")


class TableRowsPage(BaseModel):
    """행 페이지네이션 응답. 값은 화이트리스트 컬럼만 포함하며 민감 컬럼은 마스킹."""

    total: int = Field(description="필터 적용 후 전체 행 수")
    limit: int = Field(description="페이지 크기")
    offset: int = Field(description="오프셋")
    rows: list[dict[str, Any]] = Field(description="행 목록(화이트리스트 컬럼만, 마스킹 적용)")


class TableRowWrite(BaseModel):
    """행 생성/수정 요청. 화이트리스트 컬럼만 허용하며 그 외 키는 거부."""

    values: dict[str, Any] = Field(description="컬럼명→값 매핑(화이트리스트 컬럼만)")


class TableRow(BaseModel):
    """단건 행 응답 엔벌로프(get/create/update). 값은 이미 마스킹 적용됨."""

    table: str = Field(description="테이블 논리 키")
    pk: str = Field(description="행 기본키(문자열)")
    values: dict[str, Any] = Field(description="화이트리스트 컬럼 값(민감 컬럼 마스킹)")
