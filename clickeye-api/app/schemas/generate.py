"""ZIP 생성 API 스키마."""

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.preview import PreviewRequest


class GenerateRequest(PreviewRequest):
    """ZIP 생성 요청 — 위저드 설정 + API 키."""

    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="환경 변수 맵 (키: 변수명, 값: API 키 등). 서버에 저장되지 않음.",
    )
    pm_profile_id: UUID | None = Field(
        default=None,
        description="선택된 PM 프로필 ID — pm_slug보다 우선하여 DB에서 조회",
    )


class RedownloadRequest(BaseModel):
    """재다운로드 요청 — 저장된 설정 기반, env_vars만 전달."""

    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="환경 변수 맵. 서버에 저장되지 않음.",
    )
