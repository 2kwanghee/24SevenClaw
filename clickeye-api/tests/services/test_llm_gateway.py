"""LLM 게이트웨이 단위 테스트 (CE-299).

세마포어 동시성 상한, 원장 기록(성공/에러), key_source 구분 회계를 검증한다.
mock LLM 응답으로 usage 를 주입해 토큰 저장을 확인한다.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


def _mock_message(text: str, in_tok: int, out_tok: int) -> MagicMock:
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text=text)]
    usage = MagicMock()
    usage.input_tokens = in_tok
    usage.output_tokens = out_tok
    msg.usage = usage
    return msg


def _mock_service(message: MagicMock) -> MagicMock:
    """ClaudeService 스텁 — _get_client().messages.create 가 message 를 반환."""
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=message)
    svc = MagicMock()
    svc._get_client = MagicMock(return_value=client)
    svc._openai_api_key = ""
    return svc


@pytest.mark.asyncio
async def test_records_success_with_tokens(db_session) -> None:
    svc = _mock_service(_mock_message("요약", 120, 30))
    result = await llm_gateway.call(
        db_session,
        system="sys",
        messages=[{"role": "user", "content": "hi"}],
        max_tokens=100,
        request_kind="modernize_summary",
        service=svc,
    )

    assert result.text == "요약"
    assert result.input_tokens == 120
    assert result.output_tokens == 30

    rows = (await db_session.execute(select(LlmUsageLedger))).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.status == LlmUsageStatus.success
    assert row.provider == LlmProvider.anthropic
    assert row.input_tokens == 120
    assert row.output_tokens == 30
    assert row.request_kind == "modernize_summary"


@pytest.mark.asyncio
async def test_subscription_seat_has_no_cost(db_session) -> None:
    svc = _mock_service(_mock_message("x", 1_000_000, 1_000_000))
    # anthropic_api_key 미설정 → 구독시트 → 비용 None
    with patch.object(llm_gateway.settings, "anthropic_api_key", ""):
        result = await llm_gateway.call(
            db_session,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            max_tokens=50,
            request_kind="wizard_preview",
            service=svc,
        )
    assert result.key_source == LlmKeySource.subscription_seat
    assert result.cost is None


@pytest.mark.asyncio
async def test_org_api_key_computes_cost(db_session) -> None:
    svc = _mock_service(_mock_message("x", 1_000_000, 1_000_000))
    # 조직키 + 알려진 모델 → 비용 산정 (opus-4-8: 5/25 per 1M → 5 + 25 = 30)
    with (
        patch.object(llm_gateway.settings, "anthropic_api_key", "sk-ant-org"),
        patch.object(llm_gateway.settings, "anthropic_model_default", "claude-opus-4-8"),
    ):
        result = await llm_gateway.call(
            db_session,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            max_tokens=50,
            request_kind="modernize_summary",
            service=svc,
        )
    assert result.key_source == LlmKeySource.org_api_key
    assert result.cost is not None
    assert float(result.cost) == pytest.approx(30.0)


@pytest.mark.asyncio
async def test_error_path_records_error(db_session) -> None:
    client = AsyncMock()
    client.messages.create = AsyncMock(side_effect=RuntimeError("키 미설정"))
    svc = MagicMock()
    svc._get_client = MagicMock(return_value=client)
    svc._openai_api_key = ""  # 폴백 없음 → 예외 전파

    with pytest.raises(RuntimeError):
        await llm_gateway.call(
            db_session,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            max_tokens=50,
            request_kind="modernize_summary",
            service=svc,
        )

    rows = (await db_session.execute(select(LlmUsageLedger))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == LlmUsageStatus.error
    assert rows[0].meta and rows[0].meta.get("error") == "RuntimeError"


@pytest.mark.asyncio
async def test_semaphore_caps_concurrency(db_session, monkeypatch) -> None:
    """세마포어 상한을 2로 낮추고, 동시 in-flight 가 상한을 넘지 않음을 확인."""
    monkeypatch.setattr(llm_gateway, "_semaphore", asyncio.Semaphore(2))
    # 단일 세션 동시 commit 충돌 방지 — 원장 기록은 no-op 로 대체(동시성만 검증)
    monkeypatch.setattr(llm_gateway.LlmLedgerService, "record", AsyncMock())

    in_flight = 0
    peak = 0

    async def slow_create(**_kwargs):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.02)
        in_flight -= 1
        return _mock_message("ok", 1, 1)

    def make_svc() -> MagicMock:
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=slow_create)
        svc = MagicMock()
        svc._get_client = MagicMock(return_value=client)
        svc._openai_api_key = ""
        return svc

    async def one() -> None:
        await llm_gateway.call(
            db_session,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            max_tokens=10,
            request_kind="k",
            service=make_svc(),
        )

    await asyncio.gather(*[one() for _ in range(6)])
    assert peak <= 2
