"""구독 시트(다프로젝트화 P4) 요청/응답 스키마.

시트 = 팀원이 등록한 본인 구독 계정의 OAuth 토큰(`claude setup-token` 산출물).
평문 토큰은 등록 요청 body 에서만 오가고, 사용자 응답에는 절대 포함되지 않는다.
평문을 반환하는 것은 머신 수령 응답(SeatTokenResponse) 하나뿐이다.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SeatRegisterRequest(BaseModel):
    # 토큰 형식은 벤더 사정으로 바뀔 수 있으므로 접두사를 가정하지 않는다
    # (비어있지 않은 문자열 + 상한만 검증).
    oauth_token: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="`claude setup-token` 산출 OAuth 토큰(평문 — 저장 시 Fernet 암호화)",
    )


class SeatResponse(BaseModel):
    """시트 상태 응답 — 토큰(평문/마스킹 모두) 미노출."""

    seat_id: UUID
    seat_status: str = Field(description="active | exhausted | blocked")
    created_at: datetime
    updated_at: datetime | None = None


class SeatTokenRequest(BaseModel):
    project_id: UUID


class SeatTokenResponse(BaseModel):
    """머신 수령 응답 — 복호화된 평문 토큰을 담는 유일한 스키마."""

    seat_id: UUID
    user_id: UUID
    token: str


class ProjectSeatAssignRequest(BaseModel):
    seat_user_id: UUID | None = Field(
        default=None,
        description="배정할 시트 소유자의 user_id. null 이면 배정 해제(소유자 시트 폴백)",
    )


class ProjectSeatAssignResponse(BaseModel):
    project_id: UUID
    seat_user_id: UUID | None = None


class SeatProvisionItem(BaseModel):
    """DB→로컬 원장 동기화용 항목 — 평문 토큰을 담는 두 번째(유일) 경로."""

    seat_id: UUID
    user_id: UUID
    email: str
    seat_status: str = Field(description="active | exhausted | blocked")
    token: str


class SeatProvisionResponse(BaseModel):
    seats: list[SeatProvisionItem]
