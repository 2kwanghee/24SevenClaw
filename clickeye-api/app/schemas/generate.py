"""ZIP 생성 API 스키마."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.preview import PreviewRequest


class GenerateRequest(PreviewRequest):
    """ZIP 생성 요청 — 위저드 설정 + API 키."""

    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="환경 변수 맵 (키: 변수명, 값: API 키 등). 서버에 저장되지 않음.",
    )
    hook_ids: list[str] = Field(
        default_factory=list,
        description="선택된 훅 ID 목록",
    )
    pm_profile_id: UUID | None = Field(
        default=None,
        description="선택된 PM 프로필 ID — pm_slug보다 우선하여 DB에서 조회",
    )
    catalog_entry_slug: str | None = Field(
        default=None,
        description="선택된 카탈로그 엔트리 slug — ZIP에 설계 철학 및 에이전트 컨텍스트 주입",
    )
    os_id: Literal["wsl2"] = Field(
        default="wsl2",
        description="사용자 실행 환경 OS (현재 wsl2만 지원)",
    )


class RedownloadRequest(BaseModel):
    """재다운로드 요청 — 저장된 설정 기반, env_vars만 전달."""

    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="환경 변수 맵. 서버에 저장되지 않음.",
    )
