from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WizardData(BaseModel):
    """위저드 7단계 결과 데이터."""

    organization: dict[str, Any] = Field(default_factory=dict)
    solution: dict[str, Any] = Field(default_factory=dict)
    agents: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    pipelines: list[dict[str, Any]] = Field(default_factory=list)
    platform: dict[str, Any] = Field(default_factory=dict)


class WizardConfigSave(BaseModel):
    """위저드 설정 저장 요청."""

    wizard_data: WizardData


class WizardConfigResponse(BaseModel):
    """위저드 설정 조회 응답."""

    project_id: UUID
    wizard_data: WizardData | None
    updated_at: datetime

    model_config = {"from_attributes": True}
