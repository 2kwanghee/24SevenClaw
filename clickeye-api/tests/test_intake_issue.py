"""티켓 전량 자동 발급 API 테스트 (다프로젝트화 P6, D-12).

검증 축:
  1. 발급 대기 목록 — refined & 미발급만, 상태 필터를 서버가 강제:
     accepted 는 항상, pending_review 는 auto-accept opt-in 일 때만.
  2. 기계 수락 — 토글 off 403(fail-closed 최전방) / 정제 미완료 409 /
     성공 시 Project 생성 + 소유자 = 최선임 활성 superadmin.
  3. 발급 기록 — 멱등(재호출 no-op) / 비수락 409 / 빈 원장 422(스키마 강제) /
     콜백 body 에 tickets 포함.

Usage:
    cd clickeye-api && uv run pytest tests/test_intake_issue.py -v
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.intake import IntakeRequest
from app.models.project import Project
from app.models.user import User
from app.services.intake_service import (
    AUTO_ACCEPT_ENV,
    IntakeService,
    _build_callback_body,
)

TICKETS = [
    {"key": "T1", "identifier": "CE-901", "issue_id": "iid-1", "title": "설계: 스키마"},
    {"key": "T2", "identifier": "CE-902", "issue_id": "iid-2", "title": "구현: API"},
]


@pytest.fixture(autouse=True)
def _clear_toggle(monkeypatch):
    """opt-in 토글 격리 — 각 케이스가 명시적으로 켠 경우에만 기계 수락이 허용된다."""
    monkeypatch.delenv(AUTO_ACCEPT_ENV, raising=False)
    yield


@pytest.fixture(autouse=True)
def intake_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """feature_intake 킬스위치 활성화 (test_intake.py 와 동일 관례)."""
    from app.config import settings

    monkeypatch.setattr(settings, "feature_intake", True)


@pytest.fixture
async def service_key_id(db_session) -> uuid.UUID:
    _, key = await IntakeService(db_session).create_service_key("service-2", None)
    return key.id


@pytest.fixture
async def superadmin(db_session) -> User:
    admin = User(
        id=uuid.uuid4(),
        email=f"root-{uuid.uuid4().hex[:8]}@test.io",
        password_hash="x",
        display_name="시스템 운영자",
        is_active=True,
        system_role="superadmin",
    )
    db_session.add(admin)
    await db_session.commit()
    return admin


async def _make_intake(
    db_session,
    service_key_id,
    *,
    status: str = "pending_review",
    refine_status: str = "refined",
    tickets_status: str = "none",
    project_id=None,
    title: str = "테스트 수주",
) -> IntakeRequest:
    intake = IntakeRequest(
        service_key_id=service_key_id,
        input_type="structured",
        title=title,
        payload={},
        normalized_text="원문 요구사항",
        refined_text="## 구현 스펙\n- 설계\n- 구현" if refine_status == "refined" else None,
        refine_status=refine_status,
        status=status,
        tickets_status=tickets_status,
        project_id=project_id,
    )
    db_session.add(intake)
    await db_session.commit()
    await db_session.refresh(intake)
    return intake


async def _make_accepted(db_session, service_key_id, superadmin, **kw) -> IntakeRequest:
    project = Project(
        id=uuid.uuid4(),
        owner_id=superadmin.id,
        name="수주 프로젝트",
        slug=f"p-{uuid.uuid4().hex[:8]}",
    )
    db_session.add(project)
    await db_session.commit()
    return await _make_intake(
        db_session, service_key_id, status="accepted", project_id=project.id, **kw
    )


# ── 1. 발급 대기 목록 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_includes_accepted_always(
    client: AsyncClient, db_session, service_key_id, superadmin
) -> None:
    intake = await _make_accepted(db_session, service_key_id, superadmin)
    resp = await client.get("/api/v1/intake/issue/pending")
    assert resp.status_code == 200
    ids = [item["id"] for item in resp.json()]
    assert str(intake.id) in ids


@pytest.mark.asyncio
async def test_pending_review_only_when_auto_accept_enabled(
    client: AsyncClient, db_session, service_key_id, monkeypatch
) -> None:
    """토글 off 면 pending_review 는 목록에서 제외 — 기계가 손댈 수 없는 건을
    배치에 노출하지 않는다(서버 강제). on 이면 포함(배치가 auto-accept 선행)."""
    intake = await _make_intake(db_session, service_key_id, status="pending_review")

    resp_off = await client.get("/api/v1/intake/issue/pending")
    assert str(intake.id) not in [i["id"] for i in resp_off.json()]

    monkeypatch.setenv(AUTO_ACCEPT_ENV, "on")
    resp_on = await client.get("/api/v1/intake/issue/pending")
    match = [i for i in resp_on.json() if i["id"] == str(intake.id)]
    assert match and match[0]["status"] == "pending_review"  # 배치 분기 근거


@pytest.mark.asyncio
async def test_pending_excludes_unrefined_and_issued(
    client: AsyncClient, db_session, service_key_id, superadmin, monkeypatch
) -> None:
    monkeypatch.setenv(AUTO_ACCEPT_ENV, "on")
    unrefined = await _make_intake(db_session, service_key_id, refine_status="pending")
    issued = await _make_accepted(db_session, service_key_id, superadmin, tickets_status="issued")
    ids = [i["id"] for i in (await client.get("/api/v1/intake/issue/pending")).json()]
    assert str(unrefined.id) not in ids  # 정제 미완 — 분해 입력이 없다
    assert str(issued.id) not in ids  # 이미 발급 — 멱등성 앵커


# ── 2. 기계 수락 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auto_accept_disabled_returns_403(
    client: AsyncClient, db_session, service_key_id
) -> None:
    """토글 미설정 = off — 서버가 최전방에서 차단한다(fail-closed)."""
    intake = await _make_intake(db_session, service_key_id)
    resp = await client.post(f"/api/v1/intake/{intake.id}/auto-accept")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_auto_accept_requires_refined(
    client: AsyncClient, db_session, service_key_id, superadmin, monkeypatch
) -> None:
    """원문만 있는 건의 기계 수락은 품질 게이트(메타프롬프팅) 우회 — 409."""
    monkeypatch.setenv(AUTO_ACCEPT_ENV, "on")
    intake = await _make_intake(db_session, service_key_id, refine_status="pending")
    resp = await client.post(f"/api/v1/intake/{intake.id}/auto-accept")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_auto_accept_without_superadmin_409(
    client: AsyncClient, db_session, service_key_id, monkeypatch
) -> None:
    monkeypatch.setenv(AUTO_ACCEPT_ENV, "on")
    intake = await _make_intake(db_session, service_key_id)
    resp = await client.post(f"/api/v1/intake/{intake.id}/auto-accept")
    assert resp.status_code == 409  # 기계 소유자(활성 superadmin) 부재


@pytest.mark.asyncio
async def test_auto_accept_creates_project_owned_by_superadmin(
    client: AsyncClient, db_session, service_key_id, superadmin, monkeypatch
) -> None:
    monkeypatch.setenv(AUTO_ACCEPT_ENV, "on")
    intake = await _make_intake(db_session, service_key_id, title="기계 수주 건")
    resp = await client.post(f"/api/v1/intake/{intake.id}/auto-accept")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["project_id"] is not None

    project = (
        await db_session.execute(select(Project).where(Project.id == uuid.UUID(body["project_id"])))
    ).scalar_one()
    assert project.owner_id == superadmin.id  # 기계 수주 = 시스템 운영자 소유
    # 요구사항은 정제 스펙 우선(사람 accept 와 동일한 _accept_core 공유)
    assert "구현 스펙" in project.requirements_text


# ── 3. 발급 기록 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_tickets_sets_ledger_and_is_idempotent(
    client: AsyncClient, db_session, service_key_id, superadmin
) -> None:
    intake = await _make_accepted(db_session, service_key_id, superadmin)

    r1 = await client.post(f"/api/v1/intake/{intake.id}/tickets", json={"tickets": TICKETS})
    assert r1.status_code == 200, r1.text

    await db_session.refresh(intake)
    assert str(intake.tickets_status) == "issued"
    assert intake.tickets_issued_at is not None
    assert [t["identifier"] for t in intake.tickets] == ["CE-901", "CE-902"]

    # 멱등 — 다른 내용으로 재호출해도 기존 원장이 보존된다(no-op)
    other = [{"key": "T9", "identifier": "CE-999", "issue_id": "x", "title": "덮어쓰기 시도"}]
    r2 = await client.post(f"/api/v1/intake/{intake.id}/tickets", json={"tickets": other})
    assert r2.status_code == 200
    await db_session.refresh(intake)
    assert [t["identifier"] for t in intake.tickets] == ["CE-901", "CE-902"]


@pytest.mark.asyncio
async def test_record_tickets_requires_accepted(
    client: AsyncClient, db_session, service_key_id
) -> None:
    intake = await _make_intake(db_session, service_key_id, status="pending_review")
    resp = await client.post(f"/api/v1/intake/{intake.id}/tickets", json={"tickets": TICKETS})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_record_tickets_empty_rejected_by_schema(
    client: AsyncClient, db_session, service_key_id, superadmin
) -> None:
    """빈 원장은 스키마(min_length=1)가 거부 — 부분/무발급 기록은 계약상 불가."""
    intake = await _make_accepted(db_session, service_key_id, superadmin)
    resp = await client.post(f"/api/v1/intake/{intake.id}/tickets", json={"tickets": []})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_record_tickets_unknown_intake_404(client: AsyncClient) -> None:
    resp = await client.post(f"/api/v1/intake/{uuid.uuid4()}/tickets", json={"tickets": TICKETS})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_callback_body_carries_tickets(db_session, service_key_id, superadmin) -> None:
    """서비스 #2 가 콜백만으로 발급 결과를 자기 원장과 대조할 수 있어야 한다."""
    intake = await _make_accepted(db_session, service_key_id, superadmin)
    await IntakeService(db_session).record_issued_tickets(intake.id, TICKETS)
    await db_session.refresh(intake)

    body = _build_callback_body(intake)
    assert body["tickets_status"] == "issued"
    assert [t["key"] for t in body["tickets"]] == ["T1", "T2"]

    # 미발급 인테이크의 콜백은 tickets 키 없이 status 만(additive 계약)
    fresh = await _make_intake(db_session, service_key_id)
    fresh_body = _build_callback_body(fresh)
    assert fresh_body["tickets_status"] == "none"
    assert "tickets" not in fresh_body
