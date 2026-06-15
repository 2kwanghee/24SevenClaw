"""ClaudeService의 OpenAI 폴백 단위 테스트.

Anthropic 키 무효/크레딧 부족/미설정 시 동일 LLM 호출 로직(_create_message)이
OpenAI(OPENAI_API_KEY)로 폴백하는지, 레이트리밋 등 일시 오류는 폴백하지 않는지 검증한다.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import httpx
import pytest
from anthropic.types import TextBlock

from app.services.claude_service import ClaudeService


def _anthropic_error(cls: type[anthropic.APIStatusError], message: str, status: int) -> Any:
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(status, request=req)
    return cls(message, response=resp, body=None)


def _openai_completion(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    comp = MagicMock()
    comp.choices = [choice]
    return comp


def _anthropic_message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text=text)]
    return msg


@pytest.fixture
def service() -> ClaudeService:
    svc = ClaudeService(api_key="sk-ant-test")
    svc._openai_api_key = "sk-openai-test"
    svc._openai_model = "gpt-4o"
    return svc


# ── 폴백 트리거 ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auth_error_falls_back_to_openai(service: ClaudeService) -> None:
    err = _anthropic_error(anthropic.AuthenticationError, "invalid x-api-key", 401)
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(side_effect=err)
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(
        return_value=_openai_completion('{"ok": true}')
    )

    with patch.object(service, "_get_client", return_value=anthropic_client), patch.object(
        service, "_get_openai_client", return_value=openai_client
    ):
        result = await service._create_message(
            max_tokens=100, system="sys", messages=[{"role": "user", "content": "hi"}]
        )

    assert result == '{"ok": true}'
    openai_client.chat.completions.create.assert_awaited_once()
    assert openai_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_credit_error_falls_back_to_openai(service: ClaudeService) -> None:
    err = _anthropic_error(
        anthropic.BadRequestError,
        "Your credit balance is too low to access the Claude API",
        400,
    )
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(side_effect=err)
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(
        return_value=_openai_completion("drafted")
    )

    with patch.object(service, "_get_client", return_value=anthropic_client), patch.object(
        service, "_get_openai_client", return_value=openai_client
    ):
        result = await service._create_message(
            max_tokens=100, system="sys", messages=[{"role": "user", "content": "hi"}]
        )

    assert result == "drafted"


@pytest.mark.asyncio
async def test_no_anthropic_key_uses_openai(service: ClaudeService) -> None:
    service._api_key = ""  # _get_client가 RuntimeError → 폴백
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock(
        return_value=_openai_completion("ok")
    )

    with patch.object(service, "_get_openai_client", return_value=openai_client):
        result = await service._create_message(
            max_tokens=50, system="sys", messages=[{"role": "user", "content": "hi"}]
        )

    assert result == "ok"
    openai_client.chat.completions.create.assert_awaited_once()


# ── 폴백 비대상 ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_anthropic_success_does_not_call_openai(service: ClaudeService) -> None:
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(
        return_value=_anthropic_message('{"from": "anthropic"}')
    )
    openai_client = MagicMock()
    openai_client.chat.completions.create = AsyncMock()

    with patch.object(service, "_get_client", return_value=anthropic_client), patch.object(
        service, "_get_openai_client", return_value=openai_client
    ):
        result = await service._create_message(
            max_tokens=100, system="sys", messages=[{"role": "user", "content": "hi"}]
        )

    assert result == '{"from": "anthropic"}'
    openai_client.chat.completions.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_rate_limit_does_not_fall_back(service: ClaudeService) -> None:
    err = _anthropic_error(anthropic.RateLimitError, "rate limited", 429)
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(side_effect=err)

    with patch.object(service, "_get_client", return_value=anthropic_client), patch.object(
        service, "_get_openai_client"
    ) as get_openai:
        with pytest.raises(anthropic.RateLimitError):
            await service._create_message(
                max_tokens=100, system="sys", messages=[{"role": "user", "content": "hi"}]
            )
        get_openai.assert_not_called()


@pytest.mark.asyncio
async def test_no_fallback_when_openai_key_missing(service: ClaudeService) -> None:
    service._openai_api_key = ""
    err = _anthropic_error(anthropic.AuthenticationError, "invalid", 401)
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(side_effect=err)

    with patch.object(
        service, "_get_client", return_value=anthropic_client
    ), pytest.raises(anthropic.AuthenticationError):
        await service._create_message(
            max_tokens=100, system="sys", messages=[{"role": "user", "content": "hi"}]
        )


@pytest.mark.asyncio
async def test_bad_request_non_credit_reraises(service: ClaudeService) -> None:
    err = _anthropic_error(anthropic.BadRequestError, "invalid model name", 400)
    anthropic_client = AsyncMock()
    anthropic_client.messages.create = AsyncMock(side_effect=err)

    with patch.object(service, "_get_client", return_value=anthropic_client), patch.object(
        service, "_get_openai_client"
    ) as get_openai:
        with pytest.raises(anthropic.BadRequestError):
            await service._create_message(
                max_tokens=100, system="sys", messages=[{"role": "user", "content": "hi"}]
            )
        get_openai.assert_not_called()


# ── 변환/정제 헬퍼 ────────────────────────────────────────────────────────────


def test_anthropic_to_openai_messages_flattens_and_drops_cache_control() -> None:
    system = [{"type": "text", "text": "SYS", "cache_control": {"type": "ephemeral"}}]
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "A", "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "B"},
            ],
        }
    ]
    out = ClaudeService._anthropic_to_openai_messages(system, messages)
    assert out == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "A\n\nB"},
    ]


def test_anthropic_to_openai_messages_plain_strings() -> None:
    out = ClaudeService._anthropic_to_openai_messages(
        "S", [{"role": "user", "content": "hello"}]
    )
    assert out == [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "hello"},
    ]


def test_strip_code_fence_removes_json_fence() -> None:
    fenced = '```json\n{"a": 1}\n```'
    assert json.loads(ClaudeService._strip_code_fence(fenced)) == {"a": 1}


def test_strip_code_fence_noop_for_plain_text() -> None:
    assert ClaudeService._strip_code_fence('{"a": 1}') == '{"a": 1}'
