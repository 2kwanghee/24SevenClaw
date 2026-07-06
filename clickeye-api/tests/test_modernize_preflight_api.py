"""Modernize Pre-flight 게이트 통합 테스트 (Phase 5).

`generate → get → approve` 흐름과, block 판정 시 ZIP 다운로드가 403 으로 막히고
승인 후에는 정상 발급되는지를 HTTP 레벨로 검증한다.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import cast

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import require_modernize_feature
from app.main import app
from app.models.codebase_analysis import CodebaseAnalysis
from app.models.modernize_recommendation import ModernizeRecommendation
from app.models.modernize_session import ModernizeSession


@pytest.fixture(autouse=True)
def _enable_modernize_feature() -> Iterator[None]:
    original = settings.feature_modernize_enabled
    settings.feature_modernize_enabled = True
    app.dependency_overrides[require_modernize_feature] = lambda: None
    yield
    settings.feature_modernize_enabled = original
    app.dependency_overrides.pop(require_modernize_feature, None)


async def _current_user_id(client: AsyncClient, auth_headers: dict[str, str]) -> uuid.UUID:
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    return uuid.UUID(resp.json()["id"])


async def _make_session_with_analysis(
    db_session: AsyncSession,
    *,
    user_id: uuid.UUID,
    test_file_ratio: float = 0.3,
) -> ModernizeSession:
    session_row = ModernizeSession(
        user_id=user_id,
        repo_full_name="acme/widgets",
        scenario="versionup",
        status="ready",
    )
    db_session.add(session_row)
    await db_session.commit()
    await db_session.refresh(session_row)

    analysis = CodebaseAnalysis(
        session_id=cast(uuid.UUID, session_row.id),
        loc_total=1000,
        file_count=10,
        framework_signals={"test_file_ratio": test_file_ratio},
        llm_summary_md="# 요약",
    )
    db_session.add(analysis)
    await db_session.commit()
    return session_row


async def _add_recommendation(
    db_session: AsyncSession, *, session_id: uuid.UUID, **overrides: object
) -> ModernizeRecommendation:
    defaults: dict[str, object] = {
        "session_id": session_id,
        "idx": 0,
        "category": "upgrade",
        "title": "Python 3.8 → 3.12",
        "risk": "med",
        "before": {"pkg": "python", "version": "3.8"},
        "after": {"pkg": "python", "version": "3.12", "breaking_changes": []},
        "selected": True,
    }
    defaults.update(overrides)
    rec = ModernizeRecommendation(**defaults)
    db_session.add(rec)
    await db_session.commit()
    return rec


@pytest.mark.asyncio
async def test_generate_preflight_all_pass(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    uid = await _current_user_id(client, auth_headers)
    session_row = await _make_session_with_analysis(db_session, user_id=uid)
    await _add_recommendation(db_session, session_id=cast(uuid.UUID, session_row.id))

    resp = await client.post(
        f"/api/v1/modernize/sessions/{session_row.id}/preflight", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["phase"] == "preflight"
    assert body["content_json"]["overall_verdict"] == "pass"
    assert body["approved_at"] is None


@pytest.mark.asyncio
async def test_zip_download_blocked_without_preflight_approval(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    uid = await _current_user_id(client, auth_headers)
    session_row = await _make_session_with_analysis(db_session, user_id=uid)
    await _add_recommendation(db_session, session_id=cast(uuid.UUID, session_row.id))

    resp = await client.get(
        f"/api/v1/modernize/sessions/{session_row.id}/zip", headers=auth_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_blocked_when_high_risk_without_ack(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    uid = await _current_user_id(client, auth_headers)
    session_row = await _make_session_with_analysis(db_session, user_id=uid)
    await _add_recommendation(
        db_session,
        session_id=cast(uuid.UUID, session_row.id),
        risk="high",
        target_path="app/auth/login.py",
    )

    gen = await client.post(
        f"/api/v1/modernize/sessions/{session_row.id}/preflight", headers=auth_headers
    )
    assert gen.json()["content_json"]["overall_verdict"] == "block"

    approve = await client.post(
        f"/api/v1/modernize/sessions/{session_row.id}/preflight/approve",
        headers=auth_headers,
        json={"ack_high_risk": False},
    )
    assert approve.status_code == 409

    zip_resp = await client.get(
        f"/api/v1/modernize/sessions/{session_row.id}/zip", headers=auth_headers
    )
    assert zip_resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_then_zip_succeeds(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    uid = await _current_user_id(client, auth_headers)
    session_row = await _make_session_with_analysis(db_session, user_id=uid)
    await _add_recommendation(
        db_session,
        session_id=cast(uuid.UUID, session_row.id),
        risk="high",
        target_path="app/auth/login.py",
    )

    await client.post(
        f"/api/v1/modernize/sessions/{session_row.id}/preflight", headers=auth_headers
    )

    approve = await client.post(
        f"/api/v1/modernize/sessions/{session_row.id}/preflight/approve",
        headers=auth_headers,
        json={"ack_high_risk": True},
    )
    assert approve.status_code == 200
    approved_body = approve.json()
    assert approved_body["approved_at"] is not None
    assert approved_body["content_json"]["acknowledged_high_risk"] is True

    zip_resp = await client.get(
        f"/api/v1/modernize/sessions/{session_row.id}/zip", headers=auth_headers
    )
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"


@pytest.mark.asyncio
async def test_get_preflight_without_generation_returns_404(
    client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
) -> None:
    uid = await _current_user_id(client, auth_headers)
    session_row = await _make_session_with_analysis(db_session, user_id=uid)

    resp = await client.get(
        f"/api/v1/modernize/sessions/{session_row.id}/preflight", headers=auth_headers
    )
    assert resp.status_code == 404
