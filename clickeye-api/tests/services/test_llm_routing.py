"""LLM 게이트웨이 P2 훅 단위 테스트 (CE-297).

- 모델 라우팅 정책훅(_route_model): model_hint 존중, request_kind 티어 매핑, complexity 격상.
- 가격맵 외부화(_load_pricing/_compute_cost): 파일 로드·미등재 None·기존값 회귀.
- key_source 실해석(_resolve_key_source): 주입 service 실키/전역 설정/구독 세션.
"""

from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock
from sqlalchemy import select

from app.models.llm_usage_ledger import LlmKeySource, LlmUsageLedger
from app.services import llm_gateway

# ── 모델 라우팅 정책훅 ────────────────────────────────────────────────────────


def test_route_respects_model_hint() -> None:
    d = llm_gateway._route_model("classify", model_hint="claude-custom-x")
    assert d.model == "claude-custom-x"
    assert d.tier == "explicit"


def test_route_advanced_kind_uses_advanced_model() -> None:
    with patch.object(llm_gateway.settings, "anthropic_model_advanced", "claude-opus-4-8"):
        d = llm_gateway._route_model("deep_analysis")
    assert d.tier == "advanced"
    assert d.model == "claude-opus-4-8"


def test_route_default_kind_uses_default_model() -> None:
    with patch.object(llm_gateway.settings, "anthropic_model_default", "claude-sonnet-4-6"):
        d = llm_gateway._route_model("modernize_summary")
    assert d.tier == "default"
    assert d.model == "claude-sonnet-4-6"


def test_route_unknown_kind_falls_back_to_default() -> None:
    with patch.object(llm_gateway.settings, "anthropic_model_default", "claude-sonnet-4-6"):
        d = llm_gateway._route_model("some_unknown_kind")
    assert d.tier == "default"
    assert d.model == "claude-sonnet-4-6"


def test_route_light_kind_uses_light_model() -> None:
    with patch.object(llm_gateway.settings, "anthropic_model_light", "claude-haiku-4-5"):
        d = llm_gateway._route_model("extract")
    assert d.tier == "light"
    assert d.model == "claude-haiku-4-5"


def test_route_light_falls_back_to_default_when_unset() -> None:
    with (
        patch.object(llm_gateway.settings, "anthropic_model_light", ""),
        patch.object(llm_gateway.settings, "anthropic_model_default", "claude-sonnet-4-6"),
    ):
        d = llm_gateway._route_model("classify")
    assert d.tier == "light"
    assert d.model == "claude-sonnet-4-6"


def test_route_complexity_escalates_to_advanced() -> None:
    with (
        patch.object(llm_gateway.settings, "llm_route_complexity_threshold", 0.7),
        patch.object(llm_gateway.settings, "anthropic_model_advanced", "claude-opus-4-8"),
    ):
        # 일반 요약이라도 complexity 임계 이상이면 advanced 로 격상
        d = llm_gateway._route_model("modernize_summary", complexity=0.9)
    assert d.tier == "advanced"
    assert d.model == "claude-opus-4-8"


def test_route_low_complexity_no_escalation() -> None:
    with (
        patch.object(llm_gateway.settings, "llm_route_complexity_threshold", 0.7),
        patch.object(llm_gateway.settings, "anthropic_model_default", "claude-sonnet-4-6"),
    ):
        d = llm_gateway._route_model("modernize_summary", complexity=0.3)
    assert d.tier == "default"
    assert d.model == "claude-sonnet-4-6"


# ── 가격맵 외부화 ─────────────────────────────────────────────────────────────


def test_pricing_bundled_file_loads_known_models() -> None:
    llm_gateway._load_pricing.cache_clear()
    with patch.object(llm_gateway.settings, "llm_pricing_path", ""):
        pricing = llm_gateway._get_pricing()
    # 기존값 보존 회귀: opus 5/25, sonnet 3/15, haiku 1/5
    assert pricing["claude-opus-4-8"] == (Decimal("5"), Decimal("25"))
    assert pricing["claude-sonnet-4-6"] == (Decimal("3"), Decimal("15"))
    assert pricing["claude-haiku-4-5"] == (Decimal("1"), Decimal("5"))


def test_compute_cost_regression_opus_equals_30() -> None:
    """opus-4-8 1M in / 1M out = 5 + 25 = 30.0 (외부화 후 동일값 회귀)."""
    llm_gateway._load_pricing.cache_clear()
    with patch.object(llm_gateway.settings, "llm_pricing_path", ""):
        cost = llm_gateway._compute_cost(
            key_source=LlmKeySource.org_api_key,
            model="claude-opus-4-8",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
    assert cost is not None
    assert float(cost) == pytest.approx(30.0)


def test_compute_cost_unknown_model_returns_none() -> None:
    llm_gateway._load_pricing.cache_clear()
    with patch.object(llm_gateway.settings, "llm_pricing_path", ""):
        cost = llm_gateway._compute_cost(
            key_source=LlmKeySource.org_api_key,
            model="claude-nonexistent-99",
            input_tokens=1000,
            output_tokens=1000,
        )
    assert cost is None


def test_pricing_custom_path_and_missing_model(tmp_path) -> None:
    """대체 가격 파일 로드 + 미등재 모델 None."""
    custom = tmp_path / "pricing.json"
    custom.write_text(
        json.dumps({"models": {"model-a": {"input": 2, "output": 4}}}),
        encoding="utf-8",
    )
    llm_gateway._load_pricing.cache_clear()
    with patch.object(llm_gateway.settings, "llm_pricing_path", str(custom)):
        pricing = llm_gateway._get_pricing()
        assert pricing == {"model-a": (Decimal("2"), Decimal("4"))}
        # 미등재 모델 → None
        cost = llm_gateway._compute_cost(
            key_source=LlmKeySource.org_api_key,
            model="claude-opus-4-8",
            input_tokens=1000,
            output_tokens=1000,
        )
        assert cost is None
    llm_gateway._load_pricing.cache_clear()


def test_pricing_missing_file_returns_empty(tmp_path) -> None:
    missing = tmp_path / "nope.json"
    llm_gateway._load_pricing.cache_clear()
    with patch.object(llm_gateway.settings, "llm_pricing_path", str(missing)):
        assert llm_gateway._get_pricing() == {}
    llm_gateway._load_pricing.cache_clear()


# ── key_source 실해석 ─────────────────────────────────────────────────────────


def test_key_source_injected_service_real_key_is_org() -> None:
    svc = MagicMock()
    svc._api_key = "sk-ant-user"  # 실 문자열 키 → org
    with patch.object(llm_gateway.settings, "anthropic_api_key", ""):
        assert llm_gateway._resolve_key_source(service=svc) == LlmKeySource.org_api_key


def test_key_source_global_key_is_org() -> None:
    with patch.object(llm_gateway.settings, "anthropic_api_key", "sk-ant-org"):
        assert llm_gateway._resolve_key_source() == LlmKeySource.org_api_key


def test_key_source_no_key_is_subscription() -> None:
    with patch.object(llm_gateway.settings, "anthropic_api_key", ""):
        assert llm_gateway._resolve_key_source() == LlmKeySource.subscription_seat


def test_key_source_mock_nonstr_key_ignored() -> None:
    """테스트 목처럼 _api_key 가 str 이 아니면(자동 MagicMock 속성) 무시 → 전역 판별."""
    svc = MagicMock()  # svc._api_key 는 자동 MagicMock(비-str)
    with patch.object(llm_gateway.settings, "anthropic_api_key", ""):
        assert llm_gateway._resolve_key_source(service=svc) == LlmKeySource.subscription_seat


@pytest.mark.asyncio
async def test_key_source_explicit_arg_wins_in_call(db_session) -> None:
    """call() 에 명시 key_source 전달 시 해석보다 우선."""
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text="ok")]
    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 5
    msg.usage = usage
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=msg)
    svc = MagicMock()
    svc._get_client = MagicMock(return_value=client)
    svc._openai_api_key = ""

    with patch.object(llm_gateway.settings, "anthropic_api_key", "sk-ant-org"):
        result = await llm_gateway.call(
            db_session,
            system="s",
            messages=[{"role": "user", "content": "q"}],
            max_tokens=10,
            request_kind="modernize_summary",
            key_source=LlmKeySource.subscription_seat,  # 명시 → 우선
            service=svc,
        )
    assert result.key_source == LlmKeySource.subscription_seat


@pytest.mark.asyncio
async def test_call_records_route_in_meta(db_session) -> None:
    """라우팅 결정이 원장 meta.route 에 기록되는지 확인(추적성)."""
    msg = MagicMock()
    msg.content = [TextBlock(type="text", text="ok")]
    usage = MagicMock()
    usage.input_tokens = 3
    usage.output_tokens = 2
    msg.usage = usage
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=msg)
    svc = MagicMock()
    svc._get_client = MagicMock(return_value=client)
    svc._openai_api_key = ""

    await llm_gateway.call(
        db_session,
        system="s",
        messages=[{"role": "user", "content": "q"}],
        max_tokens=10,
        request_kind="deep_analysis",
        complexity=0.9,
        service=svc,
    )
    rows = (await db_session.execute(select(LlmUsageLedger))).scalars().all()
    assert len(rows) == 1
    route = rows[0].meta["route"]
    assert route["tier"] == "advanced"
    assert route["complexity"] == 0.9
