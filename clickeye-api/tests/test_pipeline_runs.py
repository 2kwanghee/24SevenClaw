"""파이프라인 실행 이력 API/서비스 테스트 (CE-363).

DB 를 타는 케이스(멱등 upsert·JSONB·조인)는 PG 전용 문법이라 `@pytest.mark.pg` 로 격리한다
(TEST_DATABASE_URL 미설정 시 conftest 가 skip). 토글 off·인증 실패는 DB 를 타지 않아
기본 SQLite 경로로 검증한다.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.config import settings
from app.database import Base
from app.models.llm_usage_ledger import (
    LlmKeySource,
    LlmProvider,
    LlmUsageLedger,
    LlmUsageStatus,
)
from app.models.pipeline_run_event import PipelineRunEvent
from app.schemas.pipeline_run import PipelineEventIn
from app.services.pipeline_run_service import PipelineRunService

# ─────────────────────────────────────────────────────────────────────────────
# DB 미탐 케이스 — 기본 SQLite 경로(client fixture)
# ─────────────────────────────────────────────────────────────────────────────


async def test_ingest_toggle_off_returns_disabled(client, monkeypatch):
    """관측 계열 공통 스위치 off → 202 {status: disabled} (에러 아님, DB 미탐)."""
    monkeypatch.setattr(settings, "feature_llm_usage_ingest", False)
    resp = await client.post(
        "/api/v1/pipeline-runs/events",
        json={"events": [{"run_id": "R1", "issue_key": "CE-1", "event": "run_done"}]},
    )
    assert resp.status_code == 202
    assert resp.json() == {"status": "disabled"}


async def test_list_requires_auth(client):
    """조회는 settings:manage 권한(JWT) 필수 — 미인증 접근은 거부된다."""
    resp = await client.get("/api/v1/pipeline-runs")
    assert resp.status_code in (401, 403)


# ─────────────────────────────────────────────────────────────────────────────
# DB 탐 케이스 — 실 Postgres 전용(@pytest.mark.pg)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def pg_db(pg_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """빈 public 스키마에 전체 테이블을 생성하고 세션을 제공한다(pg 마커 전용)."""
    async with pg_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(pg_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


def _ev(run_id: str, event: str, issue_key: str = "CE-100", **kw) -> PipelineEventIn:
    return PipelineEventIn(run_id=run_id, issue_key=issue_key, event=event, **kw)


@pytest.mark.pg
async def test_ingest_idempotent_updates_data_preserves_created_at(pg_db: AsyncSession):
    """같은 (run_id, event) 두 번 → 1행, data 갱신, created_at(최초 수신) 보존."""
    svc = PipelineRunService(pg_db)

    n1 = await svc.ingest([_ev("RUN-A", "impl_done", data={"duration_s": 10})])
    assert n1 == 1
    row1 = (
        await pg_db.execute(select(PipelineRunEvent).where(PipelineRunEvent.run_id == "RUN-A"))
    ).scalar_one()
    first_created = row1.created_at

    n2 = await svc.ingest([_ev("RUN-A", "impl_done", data={"duration_s": 99})])
    assert n2 == 1

    pg_db.expire_all()
    rows = (
        (await pg_db.execute(select(PipelineRunEvent).where(PipelineRunEvent.run_id == "RUN-A")))
        .scalars()
        .all()
    )
    assert len(rows) == 1  # 멱등 — 중복 적재 없음
    assert rows[0].data == {"duration_s": 99}  # data 갱신됨
    assert rows[0].created_at == first_created  # created_at 보존


@pytest.mark.pg
async def test_ingest_batch(pg_db: AsyncSession):
    """배치 인제스트 — 여러 이벤트가 한 번에 적재된다."""
    svc = PipelineRunService(pg_db)
    n = await svc.ingest(
        [
            _ev("RUN-B", "refine_done"),
            _ev("RUN-B", "impl_done", data={"duration_s": 5}),
            _ev("RUN-B", "run_done", data={"outcome": "merged"}),
        ]
    )
    assert n == 3
    rows = (
        (await pg_db.execute(select(PipelineRunEvent).where(PipelineRunEvent.run_id == "RUN-B")))
        .scalars()
        .all()
    )
    assert {r.event for r in rows} == {"refine_done", "impl_done", "run_done"}


@pytest.mark.pg
async def test_list_groups_by_run_derives_and_joins_usage(pg_db: AsyncSession):
    """조회: run 단위 묶임 + duration_s/outcome 파생 + 소비 토큰 조인."""
    svc = PipelineRunService(pg_db)
    base = datetime(2026, 8, 4, 12, 0, tzinfo=UTC)

    # run 1: 3 이벤트, impl_done.duration_s=42, run_done.outcome=merged
    await svc.ingest(
        [
            _ev("RUN-1", "refine_done", occurred_at=base),
            _ev(
                "RUN-1",
                "impl_done",
                occurred_at=base + timedelta(seconds=30),
                data={"duration_s": 42},
            ),
            _ev(
                "RUN-1",
                "run_done",
                occurred_at=base + timedelta(seconds=60),
                data={"outcome": "merged"},
            ),
        ]
    )
    # run 2: 다른 이슈 — 묶임 분리 확인
    await svc.ingest([_ev("RUN-2", "run_done", issue_key="CE-200", occurred_at=base)])

    # 소비 토큰 원장 — task_id=CE-100 에 2개 모델 행(같은 세션 → total_cost_usd 1회만 합산)
    for model in ("claude-opus", "claude-sonnet"):
        pg_db.add(
            LlmUsageLedger(
                id=uuid.uuid4(),
                provider=LlmProvider.anthropic,
                key_source=LlmKeySource.subscription_seat,
                model=model,
                request_kind="local_batch_implement",
                input_tokens=100,
                output_tokens=50,
                task_id="CE-100",
                session_id="sess-1",
                meta={"cache_read_input_tokens": 20, "total_cost_usd": 0.5},
                status=LlmUsageStatus.success,
            )
        )
    await pg_db.commit()

    items, total = await svc.list_runs()
    assert total == 2
    by_id = {r.run_id: r for r in items}

    r1 = by_id["RUN-1"]
    assert len(r1.events) == 3  # run 단위로 묶임
    assert r1.duration_s == 42  # impl_done.data.duration_s 파생
    assert r1.outcome == "merged"  # run_done.data.outcome 파생
    assert r1.started_at == base
    assert r1.ended_at == base + timedelta(seconds=60)
    # 토큰 조인: 2모델 합산, cache_read 는 행별 합(20+20), 비용은 세션당 1회(0.5)
    assert sorted(r1.usage.models) == ["claude-opus", "claude-sonnet"]
    assert r1.usage.input_tokens == 200
    assert r1.usage.output_tokens == 100
    assert r1.usage.cache_read_tokens == 40
    assert r1.usage.ref_cost_usd == 0.5

    r2 = by_id["RUN-2"]
    assert r2.usage.models == []  # 원장 비어도 빈 집계(실패 아님)
    assert r2.duration_s == 0  # 단일 이벤트 → 전체 폭 0초


@pytest.mark.pg
async def test_list_filters_by_issue_key(pg_db: AsyncSession):
    """issue_key 필터가 해당 티켓의 run 만 돌려준다."""
    svc = PipelineRunService(pg_db)
    await svc.ingest([_ev("RUN-X", "run_done", issue_key="CE-300")])
    await svc.ingest([_ev("RUN-Y", "run_done", issue_key="CE-301")])

    items, total = await svc.list_runs(issue_key="CE-300")
    assert total == 1
    assert items[0].run_id == "RUN-X"
