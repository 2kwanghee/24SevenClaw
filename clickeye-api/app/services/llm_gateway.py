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
import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from pathlib import Path
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
# P2: 인라인 dict → 외부 데이터 파일(app/data/llm_pricing.json)로 외부화.
# 알 수 없는(미등재) 모델은 비용 None + 경고 로그(오산정 방지).
_PRICING_FILE_DEFAULT = Path(__file__).resolve().parent.parent / "data" / "llm_pricing.json"


def _pricing_path() -> str:
    """가격맵 파일 경로 — config 오버라이드 우선, 없으면 번들 기본 파일."""
    return settings.llm_pricing_path or str(_PRICING_FILE_DEFAULT)


@cache
def _load_pricing(path_str: str) -> dict[str, tuple[Decimal, Decimal]]:
    """가격맵 파일을 로드해 {model: (input단가, output단가)} 로 파싱(경로별 1회 캐시).

    JSON 숫자는 Decimal(str(...)) 로 변환해 부동소수 오차 없이 정확값을 보존한다.
    파일 부재/파싱 실패 시 빈 맵을 반환(→ 모든 모델 cost None, 오산정 방지).
    """
    path = Path(path_str)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("LLM 가격맵 로드 실패 — 비용 산정 비활성(모든 모델 None): %s", path_str)
        return {}
    table: dict[str, tuple[Decimal, Decimal]] = {}
    for name, entry in (raw.get("models") or {}).items():
        try:
            table[name] = (Decimal(str(entry["input"])), Decimal(str(entry["output"])))
        except (KeyError, TypeError, ArithmeticError):
            logger.warning("LLM 가격맵 항목 무시(형식 오류): %s", name)
    return table


def _get_pricing() -> dict[str, tuple[Decimal, Decimal]]:
    """현재 설정 경로의 가격맵을 반환(캐시 경유)."""
    return _load_pricing(_pricing_path())


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


# 모델 라우팅 정책(P2) — request_kind → 티어 매핑 테이블 + 기본값.
# 하드코딩된 모델명 대신 티어("advanced"/"default"/"light")로 표현하고,
# 티어→실제 모델은 config 모델 필드(anthropic_model_*)를 재사용해 해석한다.
# MODEL-ROUTING.md 가이드와 정합: 무거운 설계/분석=T1(opus/advanced),
# 일반 구현/요약=T2(sonnet/default), 경량 분류/추출=T3(haiku/light).
_TIER_ADVANCED = "advanced"
_TIER_DEFAULT = "default"
_TIER_LIGHT = "light"

_ROUTE_TIER: dict[str, str] = {
    # 무거운 설계/분석 → advanced(opus 티어)
    "deep_analysis": _TIER_ADVANCED,
    "design": _TIER_ADVANCED,
    "architecture": _TIER_ADVANCED,
    # 일반 구현/요약 → default(sonnet 티어)
    "wizard_preview": _TIER_DEFAULT,
    "implement": _TIER_DEFAULT,
    # 경량 분류/추출 → light(haiku 티어)
    "classify": _TIER_LIGHT,
    "extract": _TIER_LIGHT,
}


@dataclass
class _RouteDecision:
    """라우팅 결정 — 원장 meta 추적성 기록용."""

    model: str
    tier: str
    reason: str


def _tier_model(tier: str) -> str:
    """티어 → 실제 모델(config 모델 필드 재사용). light 미설정 시 default 폴백."""
    if tier == _TIER_ADVANCED:
        return settings.anthropic_model_advanced
    if tier == _TIER_LIGHT:
        return settings.anthropic_model_light or settings.anthropic_model_default
    return settings.anthropic_model_default


def _route_model(
    request_kind: str,
    *,
    model_hint: str | None = None,
    complexity: float | None = None,
) -> _RouteDecision:
    """모델 라우팅 정책훅.

    - 명시 model_hint 가 있으면 그대로 존중(정책 우회).
    - 없으면 request_kind 매핑 테이블에서 티어 선택(미등재 → default).
    - complexity 가 임계(config) 이상이면 advanced 로 격상(복잡도는 격상만, 격하 없음).
    반환 결정은 call() 에서 원장 meta 에 기록한다(추적성).
    """
    if model_hint:
        return _RouteDecision(model=model_hint, tier="explicit", reason="model_hint")

    tier = _ROUTE_TIER.get(request_kind, _TIER_DEFAULT)
    reason = f"kind:{request_kind}->{tier}"
    if complexity is not None and complexity >= settings.llm_route_complexity_threshold:
        tier = _TIER_ADVANCED
        reason = f"complexity:{complexity}>=thr->advanced"
    return _RouteDecision(model=_tier_model(tier), tier=tier, reason=reason)


def _resolve_key_source(*, service: ClaudeService | None = None) -> LlmKeySource:
    """실제 사용된 키 출처를 판별.

    판별 근거(보수적 — 비용 계상 안전 위해 실키 존재 시 org 로 계상):
    1) 주입된 ClaudeService 의 실제 키(_api_key) 가 유효 문자열이면 → 조직/사용자 키
       (org_api_key). anthropic_key_resolver 가 반환한 사용자/org 키가 여기로 배선됨.
       (테스트 목처럼 str 이 아닌 값은 무시 — 실 키만 신뢰)
    2) 전역 settings.anthropic_api_key 설정(조직 소유 키) → org_api_key.
    3) 그 외(ANTHROPIC_API_KEY 미설정 = 구독 OAuth 세션) → subscription_seat.

    call() 이 명시 key_source 를 받으면 그쪽이 우선(이 함수는 미지정 시 폴백).
    """
    svc_key = getattr(service, "_api_key", None) if service is not None else None
    if isinstance(svc_key, str) and svc_key:
        return LlmKeySource.org_api_key
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
    pricing = _get_pricing().get(model)
    if pricing is None:
        # 미등재 모델 — Decimal('0') 오기록 대신 None + 경고(오산정 방지).
        logger.warning("LLM 가격맵 미등재 모델 — 비용 미산정(None): %s", model)
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
    complexity: float | None = None,
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

    key_source: 명시하면 우선. 기본 None 이면 _resolve_key_source(service=svc) 로
    실제 사용 키(주입된 service 의 실키 또는 전역 설정)를 기준으로 해석한다.
    model/complexity: _route_model 정책훅 입력 — model_hint 존중, 없으면 request_kind
    /complexity 기반 티어 선택. 결정은 원장 meta.route 에 기록된다.
    """
    svc = service or ClaudeService()
    decision = _route_model(request_kind, model_hint=model, complexity=complexity)
    resolved_model = decision.model
    # 명시 key_source 우선, 없으면 실제 사용 키 기준 해석(svc 의 실키/전역 설정).
    resolved_key_source = key_source or _resolve_key_source(service=svc)
    ledger = LlmLedgerService(db)

    # 라우팅 결정을 원장 meta 에 기록(추적성). 기존 meta 보존 + 가산.
    route_meta: dict[str, Any] = {"tier": decision.tier, "reason": decision.reason}
    if model:
        route_meta["requested_model"] = model
    if complexity is not None:
        route_meta["complexity"] = complexity
    ledger_meta: dict[str, Any] = {**(meta or {}), "route": route_meta}

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
                    meta={**ledger_meta, "error": type(exc).__name__},
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
                meta=ledger_meta,
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
