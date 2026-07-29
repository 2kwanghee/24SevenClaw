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

import os
import sys
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.llm_usage_ledger import LlmUsageLedger
from app.models.user_anthropic_credentials import UserAnthropicCredentials
from app.schemas.llm_ledger import LlmUsageIngestRequest
from app.services.llm_ledger_service import LlmLedgerService

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


# ── 토글 off → 실제 원장 행 0건 ──


async def test_toggle_off_writes_no_rows(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """off(기본)면 서비스에 닿지 않아 원장 행이 생기지 않는다(회귀 0 검증)."""
    resp = await client.post(_URL, json=_payload(session_id="sess-off"))
    assert resp.json() == {"status": "disabled"}

    result = await db_session.execute(
        select(LlmUsageLedger).where(LlmUsageLedger.session_id == "sess-off")
    )
    assert list(result.scalars().all()) == []


# ── org_api_key + project_id 저장 ──


async def test_org_api_key_and_project_id_stored(
    client: AsyncClient, db_session: AsyncSession, _ingest_on: None
) -> None:
    """key_source=org_api_key 와 project_id 가 원장에 그대로 저장된다."""
    pid = uuid.uuid4()
    resp = await client.post(
        _URL,
        json=_payload(
            session_id="sess-org", key_source="org_api_key", project_id=str(pid)
        ),
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "recorded"

    result = await db_session.execute(
        select(LlmUsageLedger).where(LlmUsageLedger.session_id == "sess-org")
    )
    rows = list(result.scalars().all())
    assert rows
    for row in rows:
        assert row.key_source.value == "org_api_key"
        assert row.project_id == pid


# ── 서비스 단위: IntegrityError 백스톱(프로덕션 race 방어) ──


async def test_record_usage_batch_integrityerror_is_absorbed(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record 가 IntegrityError 를 던져도 예외를 전파하지 않고 failed 로 집계한다.

    conftest 는 SQLite create_all 이라 부분 유니크 인덱스가 없어 실제 race 를
    재현할 수 없으므로, record 를 monkeypatch 해 IntegrityError 를 강제한다.
    프로덕션에서는 057 부분 유니크 인덱스가 이 예외를 발생시킨다.
    """
    svc = LlmLedgerService(db_session)
    req = LlmUsageIngestRequest.model_validate(
        {
            "session_id": "race-1",
            "models": [{"model": "claude-sonnet-5", "input_tokens": 1, "output_tokens": 2}],
        }
    )

    async def always_integrity(**_kw: object) -> None:
        raise IntegrityError("stmt", {}, Exception("unique/fk 위반"))

    monkeypatch.setattr(svc, "record", always_integrity)

    # 예외가 전파되지 않고 dict 를 반환해야 한다(202 비블로킹 계약).
    out = await svc.record_usage_batch(req)
    assert out["status"] == "skipped"  # 기록된 행 없음
    assert out.get("failed") == 1  # 재시도까지 실패 → failed 카운트 반영


# ── 로컬 빌더 ↔ 서버 스키마 계약 일치(필드명/타입 드리프트 감지) ──


def test_build_payload_matches_ingest_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    """scripts/usage_ingest.build_payload 산출물이 LlmUsageIngestRequest 로 검증된다.

    두 스위트가 서로의 계약을 모른 채 통과하다 프로덕션 422 로만 드러나는 드리프트
    (예: cache_* 키 변경)를 잡는다.
    """
    scripts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "scripts",
    )
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import usage_ingest as ui  # noqa: E402

    result_event = {
        "type": "result",
        "session_id": "sess-abc",
        "num_turns": 12,
        "duration_ms": 8993,
        "total_cost_usd": 0.35,
        "modelUsage": {
            "claude-sonnet-5": {
                "inputTokens": 2,
                "outputTokens": 378,
                "cacheReadInputTokens": 23972,
                "cacheCreationInputTokens": 57608,
            }
        },
    }
    monkeypatch.setenv("CLICKEYE_SEAT_ID", str(uuid.uuid4()))
    monkeypatch.setenv("CLICKEYE_PROJECT_ID", str(uuid.uuid4()))
    payload = ui.build_payload(
        result_event, "none", request_kind="local_batch_implement", task_id="CE-328"
    )

    # 서버 요청 스키마로 검증 — 필드명/타입이 어긋나면 여기서 ValidationError.
    obj = LlmUsageIngestRequest.model_validate(payload)
    assert obj.session_id == "sess-abc"
    assert obj.key_source.value == "subscription_seat"
    assert len(obj.models) == 1
    assert obj.models[0].model == "claude-sonnet-5"
    assert obj.models[0].cache_read_input_tokens == 23972
    assert obj.models[0].cache_creation_input_tokens == 57608
