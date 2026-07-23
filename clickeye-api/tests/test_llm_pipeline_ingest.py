"""LLM 머신 인제스트(P1.6) 테스트 — POST /api/v1/llm/ingest/pipeline + team 역매핑.

- 토글(FEATURE_LLM_AUTOINGEST) off 기본 → 202 disabled (회귀 0, 비블로킹).
- project_id 직접 지정 → queued.
- team_id 역매핑: 정확히 1건 → queued / 0건·복수건 → skipped (KB 오염 방지).
- 거버넌스 스키마 linear_team_id 하위호환.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.project_linear_credentials import ProjectLinearCredentials
from app.schemas.governance import GovernanceEvaluateRequest
from app.services.llm_ingest import resolve_project_by_team

_URL = "/api/v1/llm/ingest/pipeline"


@pytest.fixture
def _autoingest_on(monkeypatch):
    """FEATURE_LLM_AUTOINGEST 활성 + 실제 HTTP 전송은 캡처로 대체."""
    monkeypatch.setattr(settings, "feature_llm_autoingest", True)
    calls: list[tuple] = []

    def _capture(project_id, source_id, text, metadata=None):
        calls.append((project_id, source_id, text, metadata))

    # 엔드포인트 모듈 네임스페이스에 바인딩된 심볼을 교체(모듈 상단 import).
    monkeypatch.setattr("app.api.v1.llm.enqueue_ingest", _capture)
    return calls


async def _add_cred(db: AsyncSession, team_id: str) -> uuid.UUID:
    project_id = uuid.uuid4()
    db.add(
        ProjectLinearCredentials(
            project_id=project_id, encrypted_api_key="enc", team_id=team_id
        )
    )
    await db.commit()
    return project_id


# ── 엔드포인트 계약 ──


async def test_toggle_off_returns_disabled(client: AsyncClient):
    """기본(off) → 202 {status: disabled} — 에러 아님(비블로킹 계약)."""
    resp = await client.post(
        _URL, json={"team_id": "t-1", "source_id": "s", "text": "x"}
    )
    assert resp.status_code == 202
    assert resp.json() == {"status": "disabled"}


async def test_direct_project_id_queued(client: AsyncClient, _autoingest_on):
    pid = uuid.uuid4()
    resp = await client.post(
        _URL,
        json={"project_id": str(pid), "source_id": "pipeline:CE-1", "text": "머지 성공"},
    )
    assert resp.status_code == 202
    assert resp.json() == {"status": "queued", "project_id": str(pid)}
    assert len(_autoingest_on) == 1 and _autoingest_on[0][0] == pid


async def test_team_mapping_single_queued(
    client: AsyncClient, db_session: AsyncSession, _autoingest_on
):
    pid = await _add_cred(db_session, "team-solo")
    resp = await client.post(
        _URL, json={"team_id": "team-solo", "source_id": "linear:CE-2", "text": "상태전이"}
    )
    assert resp.status_code == 202
    assert resp.json() == {"status": "queued", "project_id": str(pid)}
    assert _autoingest_on[0][0] == pid


async def test_team_unmapped_skipped(client: AsyncClient, _autoingest_on):
    resp = await client.post(
        _URL, json={"team_id": "team-ghost", "source_id": "s", "text": "x"}
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "skipped" and "team-ghost" in body["reason"]
    assert _autoingest_on == []


async def test_team_ambiguous_skipped(
    client: AsyncClient, db_session: AsyncSession, _autoingest_on
):
    """복수 프로젝트가 같은 팀 공유 → 스킵(결정적, KB 네임스페이스 오염 방지)."""
    await _add_cred(db_session, "team-shared")
    await _add_cred(db_session, "team-shared")
    resp = await client.post(
        _URL, json={"team_id": "team-shared", "source_id": "s", "text": "x"}
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "skipped"
    assert _autoingest_on == []


async def test_neither_id_skipped(client: AsyncClient, _autoingest_on):
    resp = await client.post(_URL, json={"source_id": "s", "text": "x"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "skipped"


# ── 역매핑 헬퍼 단위 ──


async def test_resolve_project_by_team_rules(db_session: AsyncSession):
    pid = await _add_cred(db_session, "t-one")
    await _add_cred(db_session, "t-two")
    await _add_cred(db_session, "t-two")
    assert await resolve_project_by_team(db_session, "t-one") == pid
    assert await resolve_project_by_team(db_session, "t-two") is None  # 복수건
    assert await resolve_project_by_team(db_session, "t-none") is None  # 0건


# ── 거버넌스 스키마 하위호환 ──


def test_governance_request_accepts_linear_team_id():
    req = GovernanceEvaluateRequest(head="ralph/CE-1", linear_team_id="team-1")
    assert req.linear_team_id == "team-1"
    # 미지정(기존 호출자) 하위호환
    assert GovernanceEvaluateRequest(head="ralph/CE-1").linear_team_id is None
