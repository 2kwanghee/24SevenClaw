"""llm_gateway 구독형 전용 강제 테스트 (다프로젝트화 P3, D-10).

검증 축:
  1. 기본(토글 미설정) — 기존 동작 그대로(회귀 0). org 키 호출이 통과한다.
  2. 강제 on + org_api_key — **실행 전** 거부(SubscriptionOnlyError) + 원장 error 행
     (D-9: 관측되지 않는 차단은 없던 일이 된다) + LLM 클라이언트 미호출.
  3. 강제 on + subscription_seat — 통과(구독 경로는 막지 않는다).
  4. 강제 on + OpenAI 폴백 — 차단. 이 분기가 없으면 "Anthropic 키 부재(subscription_seat
     분류) → 유료 OpenAI 폴백 실행"이라는 조용한 종량 누수가 강제 모드를 우회한다.
  5. 위장 기록 수정 — 강제 off 라도 폴백 실사용 시 key_source 가 org_api_key 로 정정된다
     (종전: 유료 폴백이 subscription_seat·cost=None 으로 무료 위장 기록).

Usage:
    cd clickeye-api && uv run pytest tests/test_llm_gateway_subscription_only.py -v
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest
from anthropic.types import TextBlock
from sqlalchemy import select

from app.models.llm_usage_ledger import (
    LlmKeySource,
    LlmProvider,
    LlmUsageLedger,
    LlmUsageStatus,
)
from app.services import llm_gateway
from app.services.claude_service import ClaudeService
from app.services.llm_gateway import SUBSCRIPTION_ONLY_ENV, SubscriptionOnlyError


def _anthropic_error(cls: type[anthropic.APIStatusError], message: str, status: int) -> Any:
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(status, request=req)
    return cls(message, response=resp, body=None)


def _anthropic_message(text: str, input_tokens: int = 10, output_tokens: int = 5) -> MagicMock:
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text=text)]
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    msg.usage = usage
    return msg


def _openai_completion(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    comp = MagicMock()
    comp.choices = [choice]
    return comp


@pytest.fixture(autouse=True)
def _clear_toggle(monkeypatch):
    """토글 격리 — 각 케이스가 명시적으로 켠 경우에만 강제된다."""
    monkeypatch.delenv(SUBSCRIPTION_ONLY_ENV, raising=False)
    yield


@pytest.fixture
def org_service() -> ClaudeService:
    """조직 API 키(종량) 서비스 — _resolve_key_source 가 org_api_key 로 해석."""
    svc = ClaudeService(api_key="sk-ant-test")
    svc._openai_api_key = ""
    return svc


@pytest.fixture
def seat_service(monkeypatch) -> ClaudeService:
    """구독시트 서비스 — 실키·전역키 모두 없음 → subscription_seat 로 해석."""
    monkeypatch.setattr("app.services.llm_gateway.settings.anthropic_api_key", "", raising=False)
    svc = ClaudeService(api_key="")
    svc._api_key = ""
    svc._openai_api_key = ""
    return svc


async def _call(db_session, svc: ClaudeService, **kw: Any):
    return await llm_gateway.call(
        db_session,
        system="테스트",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=64,
        request_kind="test_subscription_only",
        service=svc,
        **kw,
    )


async def _ledger_rows(db_session) -> list[LlmUsageLedger]:
    rows = (
        (await db_session.execute(select(LlmUsageLedger))).scalars().all()
    )
    return [r for r in rows if r.request_kind == "test_subscription_only"]


# ── 1. 기본(미설정) — 회귀 0 ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_default_off_org_key_passes(db_session, org_service) -> None:
    """토글 미설정 = off. 종량(org) 호출이 기존대로 통과하고 원장에 success 기록."""
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=_anthropic_message("ok"))
    with patch.object(org_service, "_get_client", return_value=client):
        result = await _call(db_session, org_service)

    assert result.text == "ok"
    assert result.key_source == LlmKeySource.org_api_key
    rows = await _ledger_rows(db_session)
    assert len(rows) == 1 and rows[0].status == LlmUsageStatus.success


# ── 2. 강제 on + org — 실행 전 거부 + 원장 error ─────────────────────────────


@pytest.mark.asyncio
async def test_enforced_org_key_rejected_before_call(db_session, org_service, monkeypatch) -> None:
    monkeypatch.setenv(SUBSCRIPTION_ONLY_ENV, "on")
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=_anthropic_message("ok"))
    with (
        patch.object(org_service, "_get_client", return_value=client),
        pytest.raises(SubscriptionOnlyError),
    ):
        await _call(db_session, org_service)

    # 실행 전 거부 — LLM 클라이언트가 호출되지 않았다
    client.messages.create.assert_not_called()
    # 거부도 원장에 남는다(D-9)
    rows = await _ledger_rows(db_session)
    assert len(rows) == 1
    assert rows[0].status == LlmUsageStatus.error
    assert rows[0].key_source == LlmKeySource.org_api_key
    assert rows[0].meta["error"] == "SubscriptionOnlyError"


@pytest.mark.asyncio
async def test_enforced_explicit_key_source_also_rejected(
    db_session, seat_service, monkeypatch
) -> None:
    """명시 key_source=org_api_key 도 거부 — 해석 경로와 무관하게 종량은 종량이다."""
    monkeypatch.setenv(SUBSCRIPTION_ONLY_ENV, "on")
    with pytest.raises(SubscriptionOnlyError):
        await _call(db_session, seat_service, key_source=LlmKeySource.org_api_key)


# ── 3. 강제 on + subscription — 통과 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_enforced_subscription_seat_passes(db_session, seat_service, monkeypatch) -> None:
    monkeypatch.setenv(SUBSCRIPTION_ONLY_ENV, "on")
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=_anthropic_message("구독 ok"))
    with patch.object(seat_service, "_get_client", return_value=client):
        result = await _call(db_session, seat_service)

    assert result.text == "구독 ok"
    assert result.key_source == LlmKeySource.subscription_seat
    assert result.cost is None  # 구독시트는 비용 미산정
    rows = await _ledger_rows(db_session)
    assert len(rows) == 1 and rows[0].status == LlmUsageStatus.success


# ── 4. 강제 on — OpenAI 폴백(종량 누수) 차단 ─────────────────────────────────


@pytest.mark.asyncio
async def test_enforced_blocks_openai_fallback_leak(db_session, seat_service, monkeypatch) -> None:
    """조용한 종량 누수 차단: subscription_seat 분류 + Anthropic 인증 실패 + OpenAI 키
    존재 → 종전엔 유료 폴백이 실행됐다. 강제 모드는 폴백을 실행 전에 거부해야 한다."""
    monkeypatch.setenv(SUBSCRIPTION_ONLY_ENV, "on")
    seat_service._openai_api_key = "sk-openai-test"
    seat_service._openai_model = "gpt-4o"

    err = _anthropic_error(anthropic.AuthenticationError, "invalid x-api-key", 401)
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(side_effect=err)
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(return_value=_openai_completion("paid!"))

    with (
        patch.object(seat_service, "_get_client", return_value=anthropic_client),
        patch.object(seat_service, "_get_openai_client", return_value=openai_client),
        pytest.raises(SubscriptionOnlyError),
    ):
        await _call(db_session, seat_service)

    # 유료 OpenAI 호출이 실행되지 않았다 — 이것이 이 테스트의 존재 이유다
    openai_client.chat.completions.create.assert_not_called()
    rows = await _ledger_rows(db_session)
    assert len(rows) == 1 and rows[0].status == LlmUsageStatus.error
    assert rows[0].meta["error"] == "SubscriptionOnlyError"


# ── 5. 위장 기록 수정 (강제 off 에서도 적용되는 데이터 정확성 수정) ─────────────


@pytest.mark.asyncio
async def test_fallback_records_org_key_source_not_subscription(db_session, seat_service) -> None:
    """종전 버그: subscription_seat 분류 상태에서 유료 OpenAI 폴백이 실행되면 원장에
    subscription_seat·cost=None(무료 위장)으로 남았다. 폴백 실사용 시 key_source 는
    실제 사용 키 기준(org_api_key)으로 정정되어야 한다."""
    seat_service._openai_api_key = "sk-openai-test"
    seat_service._openai_model = "gpt-4o"

    err = _anthropic_error(anthropic.AuthenticationError, "invalid x-api-key", 401)
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(side_effect=err)
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(return_value=_openai_completion("fallback"))

    with (
        patch.object(seat_service, "_get_client", return_value=anthropic_client),
        patch.object(seat_service, "_get_openai_client", return_value=openai_client),
    ):
        result = await _call(db_session, seat_service)

    assert result.text == "fallback"
    assert result.provider == LlmProvider.openai
    assert result.key_source == LlmKeySource.org_api_key  # ← 정정된 값
    rows = await _ledger_rows(db_session)
    assert len(rows) == 1
    assert rows[0].key_source == LlmKeySource.org_api_key
    assert rows[0].provider == LlmProvider.openai


# ── 토글 의미 — is_opt_in 승계 ───────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["false", "0", "off", "", "maybe"])
async def test_toggle_non_optin_values_do_not_enforce(
    db_session, org_service, monkeypatch, value
) -> None:
    """opt-in 의미: 1/true/on/yes 외에는 전부 off — 오타로 강제가 켜지지 않는다."""
    if value:
        monkeypatch.setenv(SUBSCRIPTION_ONLY_ENV, value)
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=_anthropic_message("ok"))
    with patch.object(org_service, "_get_client", return_value=client):
        result = await _call(db_session, org_service)
    assert result.text == "ok"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["1", "true", "on", "yes"])
async def test_toggle_optin_values_enforce(db_session, org_service, monkeypatch, value) -> None:
    monkeypatch.setenv(SUBSCRIPTION_ONLY_ENV, value)
    with pytest.raises(SubscriptionOnlyError):
        await _call(db_session, org_service)


@pytest.mark.asyncio
async def test_project_task_correlation_preserved_on_rejection(
    db_session, org_service, monkeypatch
) -> None:
    """거부 원장 행에도 project_id/task_id 상관관계가 남는다 — 어느 프로젝트가 종량을
    시도했는지 추적할 수 있어야 시트 풀(P4) 설계의 입력이 된다."""
    monkeypatch.setenv(SUBSCRIPTION_ONLY_ENV, "on")
    pid = uuid.uuid4()
    with pytest.raises(SubscriptionOnlyError):
        await _call(db_session, org_service, project_id=pid, task_id="ralph/CE-999")
    rows = await _ledger_rows(db_session)
    assert rows[0].project_id == pid
    assert rows[0].task_id == "ralph/CE-999"
