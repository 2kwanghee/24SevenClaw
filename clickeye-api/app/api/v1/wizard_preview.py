"""위자드 라이브 프리뷰 엔드포인트.

POST /wizard/preview
  step + 해당 step의 입력 데이터를 받아 Claude 분석 결과를 반환한다.
  M1: company step만 지원. 미지원 step은 supported=false로 반환.

API 키 우선순위:
  1. 사용자가 설정 페이지에서 저장한 Anthropic API 키 (UserAnthropicCredentials)
  2. 서버 settings.anthropic_api_key (공용 폴백)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.anthropic_key_resolver import resolve_user_anthropic_key
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
    db: AsyncSession = Depends(get_db),
) -> WizardPreviewResponse:
    user_api_key = await resolve_user_anthropic_key(current_user.id, db)  # type: ignore[arg-type]

    service = WizardPreviewService(claude=ClaudeService(api_key=user_api_key))
    preview_result = await service.preview(step=req.step, data=req.data)

    if preview_result is not None:
        preview_result["key_source"] = "user" if user_api_key else "server"

    return WizardPreviewResponse(
        step=req.step,
        result=preview_result,
        supported=preview_result is not None,
    )
