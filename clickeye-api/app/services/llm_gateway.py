"""얇은 LLM 게이트웨이 (CE-299) — 모든 in-API AI 호출의 단일 통과 지점.

책임 (엄격히 "로깅만", 가산적·회귀 0):
- 전역 동시성 세마포어(config 상한)로 in-API LLM 호출을 제한.
- 기존 claude_service 프로바이더/폴백 경로를 재사용(재구현 금지)하되, usage(토큰)를
  얻기 위해 원시 Anthropic Message 를 캡처한다.
- 호출 1건당 원장(llm_usage_ledger)에 토큰/비용 1행 기록. 실패도 status=error 로 기록.
- 프로바이더/키출처(구독시트 vs 조직키) 구분 회계.

하지 않는 것(전부 P2): 예산 집행·레이트 거버넌스·WFQ. 모델 라우팅 정책은 빈 hook만.

원장 기록은 순수 계측이므로 주 호출 경로를 절대 깨뜨리지 않는다: 성공 호출의 원장
기록이 실패해도 결과는 그대로 반환하고, 실패 호출의 error 기록이 실패해도 원 LLM
예외를 마스킹하지 않는다(둘 다 로그만 남긴다).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_usage_ledger import (
    LlmKeySource,
    LlmProvider,
    LlmUsageStatus,
)
from app.services.claude_service import ClaudeService
from app.services.llm_ledger_service import LlmLedgerService

logger = logging.getLogger(__name__)

# 전역 동시성 세마포어 — in-API LLM 호출 총량 상한. 모듈 로드 시 1회 생성.
_semaphore = asyncio.Semaphore(settings.llm_gateway_max_concurrency)

# 조직키 비용 산정용 토큰 단가(USD, per 1M tokens). 구독시트는 산정하지 않는다.
# P2: config/DB 로 외부화. 알 수 없는 모델은 비용 None.
_PRICING_PER_MTOK: dict[str, tuple[Decimal, Decimal]] = {
    "claude-sonnet-4-6": (Decimal("3"), Decimal("15")),
    "claude-sonnet-5": (Decimal("3"), Decimal("15")),
    "claude-opus-4-8": (Decimal("5"), Decimal("25")),
    "claude-haiku-4-5": (Decimal("1"), Decimal("5")),
}


@dataclass
class LlmGatewayResult:
    """게이트웨이 호출 결과 — 텍스트 + 회계 메타."""

    text: str
    provider: LlmProvider
    key_source: LlmKeySource
    model: str
    input_tokens: int
    output_tokens: int
    cost: Decimal | None


def _concat_text(message: Any) -> str:
    """Anthropic Message 의 모든 TextBlock 을 이어붙인다.

    legacy(llm_summary) 동작과 일치 — 첫 블록만 취하면 멀티블록 응답이 잘린다.
    """
    parts: list[str] = []
    for block in getattr(message, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


def _route_model(request_kind: str, *, override: str | None = None) -> str:
    """모델 라우팅 정책훅 (빈/기본).

    현재는 명시 override 또는 config 기본 모델을 반환할 뿐이다.
    P2 확장 자리: request_kind/복잡도/비용정책에 따른 티어 선택(default↔advanced).
    """
    return override or settings.anthropic_model_default


def _resolve_key_source() -> LlmKeySource:
    """전역 키 출처 판별(추측).

    ANTHROPIC_API_KEY 미설정(구독 OAuth 세션 등) → 구독시트,
    설정(조직 소유 키) → 조직키.
    P2: 사용자별/org 키를 anthropic_key_resolver 로 배선할 때는 이 전역 추측 대신
    call() 에 key_source 를 명시 전달해야 한다.
    """
    if settings.anthropic_api_key:
        return LlmKeySource.org_api_key
    return LlmKeySource.subscription_seat


def _compute_cost(
    *,
    key_source: LlmKeySource,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal | None:
    """조직키 호출만 토큰 단가로 비용 산정.

    구독시트/미지의 모델/0토큰(폴백 포함) → None (Decimal('0') 로 오기록하지 않는다).
    """
    if key_source != LlmKeySource.org_api_key:
        return None
    if input_tokens == 0 and output_tokens == 0:
        return None
    pricing = _PRICING_PER_MTOK.get(model)
    if pricing is None:
        return None
    in_price, out_price = pricing
    cost = (
        Decimal(input_tokens) / Decimal(1_000_000) * in_price
        + Decimal(output_tokens) / Decimal(1_000_000) * out_price
    )
    return cost.quantize(Decimal("0.000001"))


async def call(
    db: AsyncSession,
    *,
    system: Any,
    messages: list[dict[str, Any]],
    max_tokens: int,
    request_kind: str,
    model: str | None = None,
    key_source: LlmKeySource | None = None,
    project_id: UUID | None = None,
    task_id: str | None = None,
    meta: dict[str, Any] | None = None,
    service: ClaudeService | None = None,
) -> LlmGatewayResult:
    """LLM 호출을 세마포어로 제한하고, 결과 usage 를 원장에 기록한다.

    프로바이더/폴백 결정은 claude_service 의미론을 재사용한다:
    Anthropic 우선 → 키 무효/크레딧 부족/미설정이면 OpenAI 폴백(설정 시).
    성공/실패 모두 원장에 1행 기록한다.

    key_source: 기본 None 이면 _resolve_key_source() 전역 추측을 사용한다. 현행
    배선(modernize_summary, service 미주입)에선 정합하나 전역 키 가정이다 —
    사용자별/org 키를 배선하는 P2 에서는 호출부가 key_source 를 명시 전달해야 한다.
    """
    svc = service or ClaudeService()
    resolved_model = _route_model(request_kind, override=model)
    resolved_key_source = key_source or _resolve_key_source()
    ledger = LlmLedgerService(db)

    async with _semaphore:
        # 1) LLM 호출. 실패 시 error 원장 기록(자체 try) 후 원 예외를 그대로 재raise.
        provider = LlmProvider.anthropic
        used_model = resolved_model
        input_tokens = 0
        output_tokens = 0
        try:
            try:
                # Anthropic 우선 — usage 를 얻기 위해 원시 Message 를 캡처한다.
                client = svc._get_client()  # noqa: SLF001 — claude_service 패턴 재사용
                message = await client.messages.create(
                    model=resolved_model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=messages,  # type: ignore[arg-type]
                )
                text = _concat_text(message)
                usage = getattr(message, "usage", None)
                input_tokens = getattr(usage, "input_tokens", 0) or 0
                output_tokens = getattr(usage, "output_tokens", 0) or 0
            except Exception as exc:  # noqa: BLE001
                # 폴백 판별은 claude_service 헬퍼 재사용(재구현 금지).
                if not (
                    svc._is_anthropic_fallback_error(exc)  # noqa: SLF001
                    and svc._openai_api_key  # noqa: SLF001
                ):
                    raise
                # OpenAI 폴백 — 텍스트만 반환(usage 미제공 → 토큰 0, 비용 None).
                # 실제 OpenAI 모델명을 기록해 claude-* 모델명 오기를 방지한다.
                # TODO(CE-299, P2): OpenAI usage(토큰) 캡처 — 현재 폴백은 0토큰 기록.
                text = await svc._call_openai(  # noqa: SLF001
                    system, messages, max_tokens
                )
                provider = LlmProvider.openai
                used_model = svc._openai_model  # noqa: SLF001
        except Exception as exc:
            # 실패 원장 기록은 자체 try로 감싸 원 LLM 예외를 절대 마스킹하지 않는다.
            try:
                await ledger.record(
                    provider=provider,
                    key_source=resolved_key_source,
                    model=used_model,
                    request_kind=request_kind,
                    input_tokens=0,
                    output_tokens=0,
                    cost=None,
                    status=LlmUsageStatus.error,
                    project_id=project_id,
                    task_id=task_id,
                    meta={**(meta or {}), "error": type(exc).__name__},
                )
            except Exception:  # noqa: BLE001
                logger.exception("LLM 원장 error 기록 실패 (원 예외는 그대로 재raise)")
            raise

        # 2) 성공 usage 기록. 여기서 실패해도 성공 호출을 error 로 뒤집지 않는다(로깅만).
        cost = _compute_cost(
            key_source=resolved_key_source,
            model=used_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        try:
            await ledger.record(
                provider=provider,
                key_source=resolved_key_source,
                model=used_model,
                request_kind=request_kind,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                status=LlmUsageStatus.success,
                project_id=project_id,
                task_id=task_id,
                meta=meta,
            )
        except Exception:  # noqa: BLE001
            logger.exception("LLM 원장 success 기록 실패 (호출 결과는 정상 반환)")

        return LlmGatewayResult(
            text=text,
            provider=provider,
            key_source=resolved_key_source,
            model=used_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )
