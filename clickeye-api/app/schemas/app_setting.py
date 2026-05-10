from typing import Any

from pydantic import BaseModel, Field


class AppSettingResponse(BaseModel):
    key: str
    value: Any
    description: str | None = None

    model_config = {"from_attributes": True}


class VariantCountUpdateRequest(BaseModel):
    value: int = Field(..., ge=2, le=5, description="프로토타입 제안 개수 (2-5)")


class AppSettingUpdateRequest(BaseModel):
    value: Any
    description: str | None = None


class LivePreviewEnabledUpdateRequest(BaseModel):
    value: bool = Field(..., description="라이브 프리뷰 기능 활성화 여부")
