"""정합성 테스트 게이트 API 테스트 (다프로젝트화 P7).

검증 축:
  1. 검증 대기 목록 — issued 만(none/verified/gate_failed 제외 — 특히 gate_failed
     의 자동 재수거 금지가 무한 재실행을 막는다). 원장(tickets) 포함(완주 대조 입력).
  2. 결과 확정 — issued→verified/gate_failed 전이 · report 가 payload 에 보존 ·
     콜백 body 에 verification 포함.
  3. 상태 기계 보호 — verified 멱등(하향 불가) · gate_failed 재제출 허용(유일한
     재검증 경로) · 미발급 409 · 빈 report 422(증거 없는 통과 주장 금지).

Usage:
    cd clickeye-api && uv run pytest tests/test_intake_verify.py -v
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from app.models.intake import IntakeRequest
from app.models.project import Project
from app.models.user import User
from app.services.intake_service import IntakeService, _build_callback_body

TICKETS = [
    {"key": "T1", "identifier": "CE-901", "issue_id": "iid-1", "title": "설계"},
    {"key": "T2", "identifier": "CE-902", "issue_id": "iid-2", "title": "구현"},
]


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
async def owner(db_session) -> User:
    u = User(
        id=uuid.uuid4(),
        email=f"o-{uuid.uuid4().hex[:8]}@test.io",
        password_hash="x",
        display_name="소유자",
        is_active=True,
    )
    db_session.add(u)
    await db_session.commit()
    return u


async def _make_intake(
    db_session, service_key_id, owner, *, tickets_status: str = "issued"
) -> IntakeRequest:
    project = Project(
        id=uuid.uuid4(), owner_id=owner.id, name="수주", slug=f"p-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(project)
    intake = IntakeRequest(
        service_key_id=service_key_id,
        input_type="structured",
        title="검증 대상 수주",
        payload={},
        refined_text="스펙",
        refine_status="refined",
        status="accepted",
        project_id=project.id,
        tickets_status=tickets_status,
        tickets=TICKETS if tickets_status != "none" else None,
    )
    db_session.add(intake)
    await db_session.commit()
    await db_session.refresh(intake)
    return intake


# ── 1. 검증 대기 목록 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pending_lists_only_issued_with_ledger(
    client: AsyncClient, db_session, service_key_id, owner
) -> None:
    issued = await _make_intake(db_session, service_key_id, owner, tickets_status="issued")
    verified = await _make_intake(db_session, service_key_id, owner, tickets_status="verified")
    failed = await _make_intake(db_session, service_key_id, owner, tickets_status="gate_failed")
    unissued = await _make_intake(db_session, service_key_id, owner, tickets_status="none")

    resp = await client.get("/api/v1/intake/verify/pending")
    assert resp.status_code == 200
    items = {i["id"]: i for i in resp.json()}

    assert str(issued.id) in items
    # 원장이 응답에 포함된다 — 배치의 완주 대조 입력
    assert [t["issue_id"] for t in items[str(issued.id)]["tickets"]] == ["iid-1", "iid-2"]
    assert str(verified.id) not in items  # 최종 상태 — 재검증 불필요
    assert str(failed.id) not in items  # 자동 재수거 금지 — 무한 재실행 방지
    assert str(unissued.id) not in items  # 발급 전 — 검증 대상 아님


# ── 2. 결과 확정 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pass_transitions_to_verified_with_report(
    client: AsyncClient, db_session, service_key_id, owner
) -> None:
    intake = await _make_intake(db_session, service_key_id, owner)
    resp = await client.post(
        f"/api/v1/intake/{intake.id}/verified",
        json={"passed": True, "report": "gates: check=0 test=0 (전량 통과)"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["tickets_status"] == "verified"

    await db_session.refresh(intake)
    v = intake.payload["verification"]
    assert v["passed"] is True and "전량 통과" in v["report"] and v["verified_at"]
    # 콜백 body 로 서비스 #2 에 최종 통보된다(체인 ⑥)
    body = _build_callback_body(intake)
    assert body["tickets_status"] == "verified"
    assert body["verification"]["passed"] is True


@pytest.mark.asyncio
async def test_fail_transitions_to_gate_failed(
    client: AsyncClient, db_session, service_key_id, owner
) -> None:
    intake = await _make_intake(db_session, service_key_id, owner)
    resp = await client.post(
        f"/api/v1/intake/{intake.id}/verified",
        json={"passed": False, "report": "gates: check=1 — ArchUnit 위반 3건"},
    )
    assert resp.status_code == 200
    assert resp.json()["tickets_status"] == "gate_failed"
    await db_session.refresh(intake)
    assert intake.payload["verification"]["passed"] is False


# ── 3. 상태 기계 보호 ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verified_is_terminal_and_idempotent(
    client: AsyncClient, db_session, service_key_id, owner
) -> None:
    """최종 상태 하향 불가 — verified 후 실패 제출이 와도 no-op 이다."""
    intake = await _make_intake(db_session, service_key_id, owner)
    await client.post(f"/api/v1/intake/{intake.id}/verified", json={"passed": True, "report": "ok"})
    resp = await client.post(
        f"/api/v1/intake/{intake.id}/verified",
        json={"passed": False, "report": "뒤늦은 실패 주장"},
    )
    assert resp.status_code == 200
    assert resp.json()["tickets_status"] == "verified"  # 흔들리지 않는다
    await db_session.refresh(intake)
    assert intake.payload["verification"]["passed"] is True  # 원 리포트 보존


@pytest.mark.asyncio
async def test_gate_failed_allows_reverification(
    client: AsyncClient, db_session, service_key_id, owner
) -> None:
    """gate_failed 재제출 = 결함 수정 후 재검증의 유일한 경로(상향만 가능)."""
    intake = await _make_intake(db_session, service_key_id, owner, tickets_status="gate_failed")
    resp = await client.post(
        f"/api/v1/intake/{intake.id}/verified",
        json={"passed": True, "report": "수정 후 재검증 — 전량 통과"},
    )
    assert resp.status_code == 200
    assert resp.json()["tickets_status"] == "verified"


@pytest.mark.asyncio
async def test_unissued_rejected_409(
    client: AsyncClient, db_session, service_key_id, owner
) -> None:
    intake = await _make_intake(db_session, service_key_id, owner, tickets_status="none")
    resp = await client.post(
        f"/api/v1/intake/{intake.id}/verified", json={"passed": True, "report": "?"}
    )
    assert resp.status_code == 409  # 발급 없이 검증 결과가 올 수 없다


@pytest.mark.asyncio
async def test_empty_report_rejected_by_schema(
    client: AsyncClient, db_session, service_key_id, owner
) -> None:
    """증거 없는 통과 주장 금지 — report min_length=1 이 스키마 수준에서 강제."""
    intake = await _make_intake(db_session, service_key_id, owner)
    resp = await client.post(
        f"/api/v1/intake/{intake.id}/verified", json={"passed": True, "report": ""}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unknown_intake_404(client: AsyncClient) -> None:
    resp = await client.post(
        f"/api/v1/intake/{uuid.uuid4()}/verified", json={"passed": True, "report": "x"}
    )
    assert resp.status_code == 404
