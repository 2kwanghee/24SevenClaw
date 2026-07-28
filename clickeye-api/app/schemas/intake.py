"""인테이크 수주 API 스키마 — Chunk A1.

IntakeCreate 는 input_type 별로 필수 본문을 분기 검증한다:
  structured → requirements(dict) / document → document{content,format} / url → source_url.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class IntakeDocument(BaseModel):
    """document 타입 본문 — 원문 텍스트와 포맷."""

    content: str = Field(..., min_length=1)
    format: str = Field(default="markdown", max_length=20)


class IntakeCreate(BaseModel):
    """외부 서비스의 인테이크 수주 요청 본문."""

    input_type: Literal["structured", "document", "url"]
    title: str = Field(..., min_length=1, max_length=200)

    # input_type 별 본문 (아래 validator 에서 분기 필수 검증)
    requirements: dict[str, Any] | None = None
    document: IntakeDocument | None = None
    source_url: str | None = Field(default=None, max_length=1000)

    # 공통 선택 필드
    target: dict[str, Any] | None = None
    priority: str | None = Field(default=None, max_length=20)
    callback_url: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _validate_body_by_type(self) -> "IntakeCreate":
        """input_type 별 필수 본문 존재 + url 스킴(http/https, SSRF 완화) 검증."""
        if self.input_type == "structured" and not self.requirements:
            raise ValueError("structured 타입은 requirements(dict)가 필수입니다.")
        if self.input_type == "document" and self.document is None:
            raise ValueError("document 타입은 document{content,format}가 필수입니다.")
        if self.input_type == "url":
            if not self.source_url:
                raise ValueError("url 타입은 source_url이 필수입니다.")
            if not self.source_url.lower().startswith(("http://", "https://")):
                raise ValueError("source_url은 http/https 스킴만 허용됩니다.")
        return self


class IntakeAcceptedResponse(BaseModel):
    """POST /intake 202 응답 — 접수 확인."""

    intake_id: UUID
    status: str


class IntakeResponse(BaseModel):
    """인테이크 상세/목록 응답 (검토 콘솔용)."""

    id: UUID
    service_key_id: UUID
    input_type: str
    title: str
    payload: dict[str, Any]
    normalized_text: str | None
    source_url: str | None
    target: dict[str, Any] | None
    priority: str | None
    callback_url: str | None
    status: str
    project_id: UUID | None
    # A3-full: 로컬 metaprompt 배치 정제 결과 (pending | refined | skipped).
    refined_text: str | None
    refine_status: str
    # CE-311: 콜백 발송 상태 (none | pending | sent | failed) — 검토 콘솔 뱃지용.
    callback_status: str
    # P6: 티켓 발급 관측 (none | issued) + 발급 원장 — 배치/콘솔이 결과를 확인한다.
    tickets_status: str = "none"
    tickets: list[dict[str, Any]] | None = None
    tickets_issued_at: datetime | None = None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class IntakeRefinePendingItem(BaseModel):
    """머신 정제 대기 목록 항목 — 로컬 정제 배치(intake_refine.sh)가 소비한다."""

    id: UUID
    title: str
    input_type: str
    normalized_text: str | None
    target: dict[str, Any] | None
    priority: str | None

    model_config = {"from_attributes": True}


class RefineSubmit(BaseModel):
    """머신 정제 결과 제출 본문 — 공백만이면 skipped 로 처리된다(규칙은 서비스가 판정)."""

    refined_text: str


class IntakeRejectRequest(BaseModel):
    """반려 사유(선택)."""

    reason: str | None = Field(default=None, max_length=1000)


# ── 티켓 전량 자동 발급 (다프로젝트화 P6, D-12) ─────────────────────────────
class IntakeIssuePendingItem(BaseModel):
    """머신 발급 대기 목록 항목 — 무인 발급 배치(intake_issue.sh)가 소비한다.

    status 로 배치의 다음 행동이 갈린다: pending_review 면 auto-accept 를 먼저 호출
    (기계 수락 opt-in 일 때만 목록에 나타난다), accepted 면 바로 분해·발급.
    """

    id: UUID
    title: str
    status: str
    project_id: UUID | None
    # 분해(claude -p) 입력 — 정제 완료 건만 목록에 오르므로 실질 비 None.
    refined_text: str | None
    # 발급 상태(DayQueued/NightQueued) 선택 힌트 — 서비스 #2 가 target 에 실은 값.
    target: dict[str, Any] | None
    priority: str | None

    model_config = {"from_attributes": True}


class IssuedTicket(BaseModel):
    """발급 원장 1건 — 분해 로컬 키(depends_on 추적)와 Linear 식별자의 대응."""

    key: str = Field(..., min_length=1, max_length=32)  # 분해 결과 로컬 키 (T1, T2…)
    identifier: str = Field(..., min_length=1, max_length=50)  # Linear 표시 키 (CE-###)
    issue_id: str = Field(..., min_length=1, max_length=100)  # Linear 내부 UUID
    title: str = Field(..., min_length=1, max_length=500)


class TicketsRecordRequest(BaseModel):
    """발급 결과 확정 본문 — 전량 발급 성공 시에만 호출된다(부분 발급 기록 금지)."""

    tickets: list[IssuedTicket] = Field(..., min_length=1)


class ServiceKeyCreate(BaseModel):
    """인테이크 서비스 키 발급 요청."""

    name: str = Field(..., min_length=1, max_length=100)
    organization_id: UUID | None = None


class ServiceKeyResponse(BaseModel):
    """서비스 키 조회 응답 — 해시/평문 미노출."""

    id: UUID
    name: str
    organization_id: UUID | None
    is_active: bool
    created_at: datetime | None

    model_config = {"from_attributes": True}


class ServiceKeyCreatedResponse(ServiceKeyResponse):
    """발급 직후 1회 한정 평문 키 포함 응답."""

    key: str
