"""로컬 배치 사용량 인제스트(CE-328) 테스트 — POST /api/v1/llm/ingest/usage.

- 토글(FEATURE_LLM_USAGE_INGEST) off 기본 → 202 disabled (회귀 0, 비블로킹).
- 머신 토큰 보호: verify_governance_token 재사용(헤더 없음 401 / 불일치 403).
- 성공: modelUsage 모델별 1행 + seat_id 축 + 캐시 토큰/런 정보 meta 보존.
- 멱등: 동일 session_id 재전송 → skipped(앱 레벨 SELECT).
- unknown seat_id → seat_id NULL + meta.unknown_seat_id 원값.

conftest 는 SQLite in-memory(create_all — 057 부분 유니크 인덱스는 없음)이므로
멱등은 앱 레벨 메커니즘(SELECT)만 검증한다(IntegrityError 백스톱은 프로덕션 전용).
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_usage_ledger import LlmUsageLedger
from app.models.user_anthropic_credentials import UserAnthropicCredentials

_URL = "/api/v1/llm/ingest/usage"


@pytest.fixture
def _ingest_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """FEATURE_LLM_USAGE_INGEST 활성(토큰 미설정 → dev 개방)."""
    monkeypatch.setattr(settings, "feature_llm_usage_ingest", True)


def _payload(session_id: str = "sess-1", **over: object) -> dict:
    body: dict = {
        "session_id": session_id,
        "request_kind": "local_batch_implement",
        "key_source": "subscription_seat",
        "task_id": "CE-328",
        "models": [
            {
                "model": "claude-sonnet-5",
                "input_tokens": 2,
                "output_tokens": 378,
                "cache_read_input_tokens": 23972,
                "cache_creation_input_tokens": 57608,
            },
            {
                "model": "claude-haiku-5",
                "input_tokens": 10,
                "output_tokens": 20,
            },
        ],
        "meta": {"total_cost_usd": 0.35, "num_turns": 12, "duration_ms": 8993},
    }
    body.update(over)
    return body


async def _add_seat(db: AsyncSession) -> uuid.UUID:
    seat_id = uuid.uuid4()
    db.add(
        UserAnthropicCredentials(
            id=seat_id,
            user_id=uuid.uuid4(),
            encrypted_api_key="enc",
            credential_type="oauth_token",
        )
    )
    await db.commit()
    return seat_id


# ── 토글 ──


async def test_toggle_off_returns_disabled(client: AsyncClient) -> None:
    """기본(off) → 202 {status: disabled} — 에러 아님(비블로킹 계약)."""
    resp = await client.post(_URL, json=_payload())
    assert resp.status_code == 202
    assert resp.json() == {"status": "disabled"}


# ── 인증(머신 토큰) ──


async def test_missing_token_401(
    client: AsyncClient, _ingest_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "governance_service_token", "usage-token")
    resp = await client.post(_URL, json=_payload())
    assert resp.status_code == 401


async def test_token_mismatch_403(
    client: AsyncClient, _ingest_on: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "governance_service_token", "usage-token")
    resp = await client.post(
        _URL, json=_payload(), headers={"X-Governance-Token": "wrong"}
    )
    assert resp.status_code == 403


# ── 유효성 ──


async def test_empty_models_422(client: AsyncClient, _ingest_on: None) -> None:
    """models 는 1개 이상 필수 → 422."""
    resp = await client.post(_URL, json=_payload(models=[]))
    assert resp.status_code == 422


# ── 성공 기록 ──


async def test_records_per_model_rows_with_seat_and_meta(
    client: AsyncClient, db_session: AsyncSession, _ingest_on: None
) -> None:
    """modelUsage 모델별 1행 + seat_id 축 + 캐시 토큰/런 정보 meta 보존."""
    seat_id = await _add_seat(db_session)
    resp = await client.post(_URL, json=_payload(seat_id=str(seat_id)))
    assert resp.status_code == 202
    assert resp.json() == {"status": "recorded", "rows": 2}

    result = await db_session.execute(
        select(LlmUsageLedger)
        .where(LlmUsageLedger.session_id == "sess-1")
        .order_by(LlmUsageLedger.model)
    )
    rows = list(result.scalars().all())
    assert len(rows) == 2
    by_model = {r.model: r for r in rows}

    sonnet = by_model["claude-sonnet-5"]
    assert sonnet.provider.value == "anthropic"
    assert sonnet.key_source.value == "subscription_seat"
    assert sonnet.status.value == "success"
    assert sonnet.cost is None  # v1 은 비용 미산정
    assert sonnet.seat_id == seat_id
    assert sonnet.session_id == "sess-1"
    assert sonnet.task_id == "CE-328"
    assert sonnet.input_tokens == 2 and sonnet.output_tokens == 378
    # 캐시 토큰(모델별) + 공유 런 정보(요청 meta) 를 행 meta 에 보존.
    assert sonnet.meta["cache_read_input_tokens"] == 23972
    assert sonnet.meta["cache_creation_input_tokens"] == 57608
    assert sonnet.meta["total_cost_usd"] == 0.35
    assert sonnet.meta["num_turns"] == 12

    # 캐시 토큰 미제공 모델은 0 으로 기록.
    haiku = by_model["claude-haiku-5"]
    assert haiku.meta["cache_read_input_tokens"] == 0
    assert haiku.meta["cache_creation_input_tokens"] == 0


# ── 멱등 ──


async def test_duplicate_session_skipped(
    client: AsyncClient, db_session: AsyncSession, _ingest_on: None
) -> None:
    """동일 session_id 재전송 → 모든 모델 중복 → skipped, 행 증가 없음."""
    first = await client.post(_URL, json=_payload())
    assert first.json() == {"status": "recorded", "rows": 2}

    second = await client.post(_URL, json=_payload())
    assert second.status_code == 202
    assert second.json()["status"] == "skipped"

    result = await db_session.execute(
        select(LlmUsageLedger).where(LlmUsageLedger.session_id == "sess-1")
    )
    assert len(list(result.scalars().all())) == 2  # 재전송으로 늘지 않음


# ── seat_id 사전검증 ──


async def test_unknown_seat_id_nulled_with_meta(
    client: AsyncClient, db_session: AsyncSession, _ingest_on: None
) -> None:
    """미존재 seat_id → seat_id NULL + meta.unknown_seat_id 에 원값(FK 500 방지)."""
    ghost = uuid.uuid4()
    resp = await client.post(
        _URL, json=_payload(session_id="sess-ghost", seat_id=str(ghost))
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "recorded"

    result = await db_session.execute(
        select(LlmUsageLedger).where(LlmUsageLedger.session_id == "sess-ghost")
    )
    rows = list(result.scalars().all())
    assert rows
    for row in rows:
        assert row.seat_id is None
        assert row.meta["unknown_seat_id"] == str(ghost)
