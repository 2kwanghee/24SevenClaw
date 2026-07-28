"""딜리버리 이벤트 기록면 — 타임라인·집계 API 테스트 (다프로젝트화 P9, D-8·D-9).

검증 축:
  1. 전이 훅 통합 — 무인 체인 전 구간(수신→정제→기계수락→발급→검증)이 이벤트로
     남고, 타임라인이 **발생 순서**로 재구성한다.
  2. 실패 전이 기록(D-9) — verification_failed 도 성공과 동일하게 남는다.
     기록되지 않는 실패는 사후에 없던 일이 된다.
  3. 계측 격리 — 이벤트 기록이 터져도 전이(주 경로)는 커밋된다.
  4. 집계 — 체인 단계별 버킷 수가 정확하다(반려는 모수에서 빠진다).
  5. 접근 통제 — 미인증/권한 부족 차단, 미존재 인테이크 404.

Usage:
    cd clickeye-api && uv run pytest tests/test_delivery_events.py -v
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update

from app.models.delivery_event import DeliveryEvent
from app.models.intake import IntakeRequest, IntakeServiceKey
from app.models.user import User
from app.schemas.intake import IntakeCreate
from app.services import intake_service as intake_service_module
from app.services.intake_service import AUTO_ACCEPT_ENV, IntakeService

TICKETS = [
    {"key": "T1", "identifier": "CE-901", "issue_id": "iid-1", "title": "설계: 스키마"},
    {"key": "T2", "identifier": "CE-902", "issue_id": "iid-2", "title": "구현: API"},
]


# ---------------------------------------------------------------------------
# 헬퍼 / 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def intake_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """feature_intake 킬스위치 활성화 (test_intake_verify.py 와 동일 관례)."""
    from app.config import settings

    monkeypatch.setattr(settings, "feature_intake", True)


@pytest.fixture(autouse=True)
def _clear_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    """기계 수락 opt-in 격리 — 명시적으로 켠 케이스만 허용된다."""
    monkeypatch.delenv(AUTO_ACCEPT_ENV, raising=False)


@pytest.fixture
async def service_key(db_session) -> IntakeServiceKey:
    _, key = await IntakeService(db_session).create_service_key("service-2", None)
    return key


@pytest.fixture
async def admin_headers(client: AsyncClient, db_session) -> dict[str, str]:
    """control_tower:read 세션. superadmin 이므로 기계 수락 소유자도 겸한다."""
    creds = {"email": "chain-admin@events.io", "password": "pw12345678"}
    await client.post("/api/v1/auth/register", json={**creds, "display_name": "운영자"})
    token = (await client.post("/api/v1/auth/login", json=creds)).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    await db_session.execute(
        update(User)
        .where(User.id == uuid.UUID(me.json()["id"]))
        .values(system_role="superadmin")
    )
    await db_session.commit()
    return headers


def _create_body(title: str = "무인 체인 수주") -> IntakeCreate:
    return IntakeCreate(
        input_type="structured", title=title, requirements={"goal": "타임라인 재구성"}
    )


async def _run_chain_to_issued(
    db_session, service_key: IntakeServiceKey, *, title: str = "무인 체인 수주"
) -> IntakeRequest:
    """수신→정제→기계수락→발급까지 전이 메서드를 실제로 통과시킨다(검증 전 상태)."""
    service = IntakeService(db_session)
    intake = await service.create_intake(service_key, _create_body(title), None)
    await service.submit_refined(intake.id, "구현 스펙: 타임라인 API 를 붙인다")
    await service.machine_accept(intake.id)
    await service.record_issued_tickets(intake.id, TICKETS)
    return intake


async def _seed_intake(
    db_session,
    service_key: IntakeServiceKey,
    *,
    status: str,
    refine_status: str,
    tickets_status: str = "none",
) -> IntakeRequest:
    """집계 검증용 상태 조합 시드 — 전이를 거치지 않고 상태만 직접 만든다."""
    intake = IntakeRequest(
        service_key_id=service_key.id,
        input_type="structured",
        title="집계 대상",
        payload={},
        status=status,
        refine_status=refine_status,
        refined_text="스펙" if refine_status == "refined" else None,
        tickets_status=tickets_status,
    )
    db_session.add(intake)
    await db_session.commit()
    await db_session.refresh(intake)
    return intake


async def _timeline(
    client: AsyncClient, intake_id: uuid.UUID, headers: dict[str, str]
) -> dict[str, Any]:
    resp = await client.get(f"/api/v1/intake/{intake_id}/timeline", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ── 1. 전이 훅 통합 — 체인 전 구간이 순서대로 남는다 ─────────────────────────


@pytest.mark.asyncio
async def test_full_chain_events_in_occurrence_order(
    client: AsyncClient, db_session, service_key, admin_headers, monkeypatch
) -> None:
    """E2E 리허설과 동일한 전이열이 타임라인에서 그대로 재구성된다(수용 기준)."""
    monkeypatch.setenv(AUTO_ACCEPT_ENV, "on")
    intake = await _run_chain_to_issued(db_session, service_key)
    await IntakeService(db_session).record_verification(
        intake.id, passed=True, report="gates: check=0 test=0 (전량 통과)"
    )

    body = await _timeline(client, intake.id, admin_headers)
    assert [e["event_type"] for e in body["events"]] == [
        "received",
        "refined",
        "machine_accepted",
        "tickets_issued",
        "verification_passed",
    ]
    # 상태 스냅샷도 같은 응답에 실린다(대시보드가 배지로 쓴다)
    assert body["status"] == "accepted"
    assert body["refine_status"] == "refined"
    assert body["tickets_status"] == "verified"
    assert body["title"] == "무인 체인 수주"
    # 무인 체인은 사람 개입 0 — 액터가 전량 machine 이다
    assert {e["actor_type"] for e in body["events"]} == {"machine"}
    # 구조화 부가정보 보존 — 발급 건수는 meta 에 남는다
    issued = next(e for e in body["events"] if e["event_type"] == "tickets_issued")
    assert issued["meta"]["count"] == len(TICKETS)
    assert "CE-901" in issued["detail"]


# ── 2. 실패 전이 기록 (D-9) ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_failed_verification_is_recorded(
    client: AsyncClient, db_session, service_key, admin_headers, monkeypatch
) -> None:
    """게이트 실패도 타임라인에 남는다 — 정지 원인 추적이 이 기록면의 존재 이유다."""
    monkeypatch.setenv(AUTO_ACCEPT_ENV, "on")
    intake = await _run_chain_to_issued(db_session, service_key)
    await IntakeService(db_session).record_verification(
        intake.id, passed=False, report="gates: check=1 — ArchUnit 위반 3건"
    )

    body = await _timeline(client, intake.id, admin_headers)
    types = [e["event_type"] for e in body["events"]]
    assert "verification_failed" in types
    assert "verification_passed" not in types
    failed = next(e for e in body["events"] if e["event_type"] == "verification_failed")
    assert failed["meta"]["passed"] is False
    assert "ArchUnit" in failed["detail"]  # 실패 사유 1행이 경위로 남는다
    assert body["tickets_status"] == "gate_failed"


# ── 3. 계측 격리 — 기록 실패가 전이를 깨뜨리지 않는다 ────────────────────────


@pytest.mark.asyncio
async def test_event_failure_does_not_break_transition(
    db_session, service_key, monkeypatch
) -> None:
    """이벤트 기록은 순수 계측이다 — 터져도 전이는 커밋된 채로 남는다(수용 기준)."""
    service = IntakeService(db_session)
    intake = await service.create_intake(service_key, _create_body(), None)

    def _boom(**_kwargs: Any) -> DeliveryEvent:
        raise RuntimeError("이벤트 기록 강제 실패")

    monkeypatch.setattr(intake_service_module, "DeliveryEvent", _boom)
    refined = await service.submit_refined(intake.id, "구현 스펙: 계측 격리 확인")

    assert str(refined.refine_status) == "refined"
    assert refined.refined_text == "구현 스펙: 계측 격리 확인"
    # 유실된 것은 계측뿐 — 패치 이전에 남은 received 만 존재한다
    rows = (
        await db_session.execute(
            select(DeliveryEvent).where(DeliveryEvent.intake_id == intake.id)
        )
    ).scalars().all()
    assert [str(e.event_type) for e in rows] == ["received"]


# ── 4. 체인 단계별 집계 ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_overview_buckets(
    client: AsyncClient, db_session, service_key, admin_headers
) -> None:
    """버킷 정의대로 센다 — 반려는 모수(total)에서 빠지고 자기 버킷에만 잡힌다."""
    await _seed_intake(db_session, service_key, status="pending_review", refine_status="pending")
    await _seed_intake(db_session, service_key, status="pending_review", refine_status="pending")
    # 정제 완료·미발급은 status 가 pending_review 든 accepted 든 '발급 대기'다
    await _seed_intake(db_session, service_key, status="pending_review", refine_status="refined")
    await _seed_intake(db_session, service_key, status="accepted", refine_status="refined")
    await _seed_intake(
        db_session, service_key, status="accepted", refine_status="refined",
        tickets_status="issued",
    )
    await _seed_intake(
        db_session, service_key, status="accepted", refine_status="refined",
        tickets_status="verified",
    )
    await _seed_intake(
        db_session, service_key, status="accepted", refine_status="refined",
        tickets_status="gate_failed",
    )
    await _seed_intake(db_session, service_key, status="rejected", refine_status="pending")

    resp = await client.get("/api/v1/intake/overview", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "total": 7,  # 반려 1건 제외
        "pending_refine": 2,
        "pending_issue": 2,
        "implementing": 1,
        "verified": 1,
        "gate_failed": 1,
        "rejected": 1,
    }


@pytest.mark.asyncio
async def test_overview_empty_is_all_zero(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    """인테이크가 없어도 200 + 전 버킷 0 — 대시보드가 빈 상태를 렌더할 수 있다."""
    resp = await client.get("/api/v1/intake/overview", headers=admin_headers)
    assert resp.status_code == 200
    assert set(resp.json().values()) == {0}


# ── 5. 접근 통제 ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_timeline_unknown_intake_404(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    resp = await client.get(f"/api/v1/intake/{uuid.uuid4()}/timeline", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_records_require_authentication(client: AsyncClient) -> None:
    """미인증 조회 차단 — 기록면은 사람 조회용이고 머신 토큰 경로가 아니다."""
    assert (
        await client.get(f"/api/v1/intake/{uuid.uuid4()}/timeline")
    ).status_code in (401, 403)
    assert (await client.get("/api/v1/intake/overview")).status_code in (401, 403)


@pytest.mark.asyncio
async def test_records_forbidden_without_control_tower_read(client: AsyncClient) -> None:
    """기본 역할(member)은 control_tower:read 가 없다 — 403."""
    creds = {"email": "member@events.io", "password": "pw12345678"}
    await client.post("/api/v1/auth/register", json={**creds, "display_name": "일반"})
    token = (await client.post("/api/v1/auth/login", json=creds)).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get(f"/api/v1/intake/{uuid.uuid4()}/timeline", headers=headers)
    assert resp.status_code == 403
    assert (await client.get("/api/v1/intake/overview", headers=headers)).status_code == 403
