"""위자드 라이브 프리뷰 서비스.

M1: company step만 지원 (ClaudeService.analyze_solution 재사용).
이후 단계는 M2+에서 추가한다.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import anthropic

from app.services.claude_service import ClaudeService

logger = logging.getLogger(__name__)

_CACHE_TTL = 60  # seconds
_MIN_PROMPT_LENGTH = 10


def _input_hash(step: str, data: dict[str, Any]) -> str:
    payload = json.dumps({"step": step, "data": data}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


class WizardPreviewService:
    """위자드 각 step의 입력 데이터를 Claude로 분석해 프리뷰 결과를 반환한다."""

    def __init__(self, claude: ClaudeService) -> None:
        self._claude = claude

    async def preview(self, step: str, data: dict[str, Any]) -> dict[str, Any] | None:
        """step + data → 프리뷰 결과. 미지원 step은 None 반환."""
        if step == "company":
            return await self._preview_company(data)
        return None

    async def _preview_company(self, data: dict[str, Any]) -> dict[str, Any]:
        prompt: str = data.get("solutionRequest", "").strip()
        if len(prompt) < _MIN_PROMPT_LENGTH:
            return {"status": "too_short"}

        org_context: dict[str, Any] = {
            "companyName": data.get("companyName", ""),
            "industry": data.get("industry", ""),
            "companySize": data.get("companySize", ""),
            "businessType": data.get("businessType", ""),
            "techStack": data.get("techStack", []),
            "mainProduct": data.get("mainProduct", ""),
        }

        cache_key = f"wizard_preview:{_input_hash('company', {**org_context, 'prompt': prompt})}"

        # Redis 캐시 조회 (연결 실패 시 무시)
        try:
            from app.redis import get_redis  # noqa: PLC0415
            redis = get_redis()
            cached = await redis.get(cache_key)
            if cached:
                result: dict[str, Any] = json.loads(cached)
                result["cached"] = True
                return result
        except Exception:
            pass

        try:
            result = await self._claude.analyze_solution(prompt=prompt, org_context=org_context)
        except anthropic.AuthenticationError:
            logger.warning("wizard_preview: Anthropic API 인증 실패 — API 키를 확인하세요")
            return {"status": "api_auth_error"}
        except anthropic.BadRequestError as exc:
            # 크레딧 부족 등 400 에러 — 서버 500 대신 graceful fallback
            msg = str(exc)
            if "credit balance is too low" in msg:
                logger.warning("wizard_preview: Anthropic API 크레딧 부족")
                return {"status": "api_credit_error"}
            logger.warning("wizard_preview: Anthropic API 400 에러 — %s", msg)
            return {"status": "api_error"}
        except anthropic.APIError as exc:
            logger.warning("wizard_preview: Anthropic API 에러 — %s", exc)
            return {"status": "api_error"}
        except Exception as exc:
            logger.exception("wizard_preview: 예기치 않은 에러 — %s", exc)
            return {"status": "error"}

        result["status"] = "ok"
        result["cached"] = False

        # Redis 캐시 저장 (연결 실패 시 무시)
        try:
            from app.redis import get_redis  # noqa: PLC0415
            redis = get_redis()
            await redis.setex(cache_key, _CACHE_TTL, json.dumps(result, ensure_ascii=False))
        except Exception:
            pass

        return result
