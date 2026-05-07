"""위자드 라이브 프리뷰 엔드포인트.

POST /wizard/preview
  step + 해당 step의 입력 데이터를 받아 Claude 분석 결과를 반환한다.
  M1: company step만 지원. 미지원 step은 supported=false로 반환.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.user import User
from app.services.claude_service import ClaudeService
from app.services.wizard_preview_service import WizardPreviewService

router = APIRouter(prefix="/wizard", tags=["wizard-preview"])


class WizardPreviewRequest(BaseModel):
    step: str
    data: dict[str, Any]


class WizardPreviewResponse(BaseModel):
    step: str
    result: dict[str, Any] | None = None
    supported: bool


@router.post("/preview", response_model=WizardPreviewResponse)
async def wizard_preview(
    req: WizardPreviewRequest,
    _current_user: User = Depends(get_current_user),
) -> WizardPreviewResponse:
    service = WizardPreviewService(claude=ClaudeService())
    result = await service.preview(step=req.step, data=req.data)
    return WizardPreviewResponse(
        step=req.step,
        result=result,
        supported=result is not None,
    )
