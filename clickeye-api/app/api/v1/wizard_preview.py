"""위자드 라이브 프리뷰 엔드포인트.

POST /wizard/preview
  step + 해당 step의 입력 데이터를 받아 Claude 분석 결과를 반환한다.
  M1: company step만 지원. 미지원 step은 supported=false로 반환.

API 키 정책:
  위저드 프리뷰는 사용자가 아직 본인 키를 입력하기 전의 설계/체험 단계이므로
  항상 서버 키(settings.anthropic_api_key)로 동작한다. 서버 키가 무효/크레딧 부족이면
  ClaudeService 내부에서 OpenAI(OPENAI_API_KEY)로 자동 폴백한다.
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
    current_user: User = Depends(get_current_user),
) -> WizardPreviewResponse:
    # 설계/체험 단계 — 항상 서버 키 사용(사용자 키는 로컬 실행 단계에서만).
    service = WizardPreviewService(claude=ClaudeService())
    preview_result = await service.preview(step=req.step, data=req.data)

    if preview_result is not None:
        preview_result["key_source"] = "server"

    return WizardPreviewResponse(
        step=req.step,
        result=preview_result,
        supported=preview_result is not None,
    )
