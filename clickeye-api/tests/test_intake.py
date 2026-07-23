"""인테이크 수주 API (Chunk A1) 테스트.

핵심 검증:
- 킬스위치: FEATURE_INTAKE 기본 off → 전 라우트 404
- 서비스 키 인증: 헤더 없음/무효 키 401, 유효 키 202
- 3형태 접수(structured/document/url) + url fetch 실패 시 202 유지 + fetch_error 기록
- 멱등: 동일 Idempotency-Key 재수신 → 동일 intake_id, 레코드 1건
- accept → Project 생성(organization/requirements_text/project_type) + project_id 연결
- reject → rejected 전이, 재처리 409
- 조직 스코프: superadmin 전체 / admin 자기 조직 키 접수분만
- 키 관리: superadmin 전용, 평문 1회 반환, 목록 해시 미노출, 비활성화 후 401
"""

from __future__ import annotations

import hashlib
import hmac
import json
import socket
import uuid

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.intake import IntakeRequest, IntakeServiceKey
from app.models.organization import Organization
from app.models.project import Project
from app.models.user import User
from app.services import intake_service as intake_service_module

RAW_KEY = "test-intake-service-key-plaintext"


# ---------------------------------------------------------------------------
# 헬퍼 / 픽스처
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pw12345678", "display_name": "t"},
    )
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "pw12345678"})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return headers, me.json()["id"]


async def _set_role(
    db: AsyncSession, user_id: str, role: str, organization_id: uuid.UUID | None = None
) -> None:
    await db.execute(
        update(User)
        .where(User.id == uuid.UUID(user_id))
        .values(system_role=role, organization_id=organization_id)
    )
    await db.commit()


@pytest.fixture
def intake_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """feature_intake 킬스위치 활성화."""
    monkeypatch.setattr(settings, "feature_intake", True)


@pytest.fixture
async def org(db_session: AsyncSession) -> Organization:
    o = Organization(company_name="테스트고객사")
    db_session.add(o)
    await db_session.commit()
    await db_session.refresh(o)
    return o


@pytest.fixture
async def service_key(db_session: AsyncSession, org: Organization) -> IntakeServiceKey:
    """조직 소속 활성 서비스 키(평문 RAW_KEY)를 직접 시드한다."""
    key = IntakeServiceKey(
        name="외부수주서비스",
        key_hash=hashlib.sha256(RAW_KEY.encode()).hexdigest(),
        organization_id=org.id,
    )
    db_session.add(key)
    await db_session.commit()
    await db_session.refresh(key)
    return key


def _machine_headers(idempotency: str | None = None) -> dict[str, str]:
    headers = {"X-ClickEye-Service-Key": RAW_KEY}
    if idempotency:
        headers["Idempotency-Key"] = idempotency
    return headers


def _structured_body(title: str = "쇼핑몰 구축") -> dict:
    return {
        "input_type": "structured",
        "title": title,
        "requirements": {"기능": ["회원가입", "결제"], "예산": "5000만원"},
        "priority": "high",
        "callback_url": "https://partner.example.com/hook",
    }


# ---------------------------------------------------------------------------
# 킬스위치
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_killswitch_off_returns_404(client: AsyncClient) -> None:
    """FEATURE_INTAKE 기본 off → 전 라우트 404 (존재 은닉)."""
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    assert resp.status_code == 404
    assert (await client.get("/api/v1/intake")).status_code == 404
    assert (await client.get("/api/v1/intake/service-keys")).status_code == 404


# ---------------------------------------------------------------------------
# 서비스 키 인증
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_key_401(client: AsyncClient, intake_enabled: None) -> None:
    resp = await client.post("/api/v1/intake", json=_structured_body())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_key_401(
    client: AsyncClient, intake_enabled: None, service_key: IntakeServiceKey
) -> None:
    resp = await client.post(
        "/api/v1/intake",
        json=_structured_body(),
        headers={"X-ClickEye-Service-Key": "wrong-key"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 3형태 접수
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_structured(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
) -> None:
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending_review"

    intake = await db_session.get(IntakeRequest, uuid.UUID(body["intake_id"]))
    assert intake is not None
    assert intake.input_type == "structured"
    assert "회원가입" in (intake.normalized_text or "")
    assert intake.payload["requirements"]["예산"] == "5000만원"


@pytest.mark.asyncio
async def test_create_document(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
) -> None:
    resp = await client.post(
        "/api/v1/intake",
        json={
            "input_type": "document",
            "title": "요구사항 정의서 v1",
            "document": {"content": "# 개요\n결제 시스템 구축", "format": "markdown"},
        },
        headers=_machine_headers(),
    )
    assert resp.status_code == 202
    intake = await db_session.get(IntakeRequest, uuid.UUID(resp.json()["intake_id"]))
    assert intake.normalized_text == "# 개요\n결제 시스템 구축"


@pytest.mark.asyncio
async def test_create_url_fetch_success(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """url 타입 — fetch 성공 시 추출 텍스트가 normalized_text 에 저장된다."""

    async def _fake_fetch(url: str) -> str:
        assert url == "https://spec.example.com/rfp"
        return "RFP 본문 텍스트"

    monkeypatch.setattr(intake_service_module, "_fetch_url_text", _fake_fetch)
    resp = await client.post(
        "/api/v1/intake",
        json={"input_type": "url", "title": "RFP", "source_url": "https://spec.example.com/rfp"},
        headers=_machine_headers(),
    )
    assert resp.status_code == 202
    intake = await db_session.get(IntakeRequest, uuid.UUID(resp.json()["intake_id"]))
    assert intake.normalized_text == "RFP 본문 텍스트"
    assert intake.source_url == "https://spec.example.com/rfp"


@pytest.mark.asyncio
async def test_create_url_fetch_failure_still_202(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fetch 실패해도 요청은 실패시키지 않고 payload.fetch_error 에 사유를 기록한다."""

    async def _fake_fetch(url: str) -> str:
        raise ValueError("허용되지 않는 Content-Type: application/pdf")

    monkeypatch.setattr(intake_service_module, "_fetch_url_text", _fake_fetch)
    resp = await client.post(
        "/api/v1/intake",
        json={"input_type": "url", "title": "RFP", "source_url": "https://spec.example.com/x"},
        headers=_machine_headers(),
    )
    assert resp.status_code == 202
    intake = await db_session.get(IntakeRequest, uuid.UUID(resp.json()["intake_id"]))
    assert intake.normalized_text is None
    assert "Content-Type" in intake.payload["fetch_error"]


@pytest.mark.asyncio
async def test_validation_by_input_type(
    client: AsyncClient, intake_enabled: None, service_key: IntakeServiceKey
) -> None:
    """input_type 별 필수 본문 누락/비허용 스킴 → 422."""
    cases = [
        {"input_type": "structured", "title": "t"},  # requirements 누락
        {"input_type": "document", "title": "t"},  # document 누락
        {"input_type": "url", "title": "t"},  # source_url 누락
        {"input_type": "url", "title": "t", "source_url": "ftp://x.com/a"},  # 스킴 위반
    ]
    for body in cases:
        resp = await client.post("/api/v1/intake", json=body, headers=_machine_headers())
        assert resp.status_code == 422, body


# ---------------------------------------------------------------------------
# 멱등
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_idempotency_returns_same_record(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
) -> None:
    h = _machine_headers(idempotency="idem-001")
    first = await client.post("/api/v1/intake", json=_structured_body(), headers=h)
    second = await client.post("/api/v1/intake", json=_structured_body(), headers=h)
    assert first.status_code == second.status_code == 202
    assert first.json()["intake_id"] == second.json()["intake_id"]

    rows = (await db_session.execute(select(IntakeRequest))).scalars().all()
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# 검토 목록 / 조직 스코프 / 권한
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_requires_admin(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
) -> None:
    headers, _uid = await _register_and_login(client, "member@intake.com")
    resp = await client.get("/api/v1/intake", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_org_scope(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
) -> None:
    """superadmin 은 전체, admin 은 자기 조직 키 접수분만, 무조직 admin 은 빈 목록."""
    await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())

    # 타 조직 키로 접수 1건 추가
    other_key = IntakeServiceKey(
        name="타조직서비스", key_hash=hashlib.sha256(b"other-raw").hexdigest()
    )
    db_session.add(other_key)
    await db_session.commit()
    await client.post(
        "/api/v1/intake",
        json=_structured_body(title="타조직 수주"),
        headers={"X-ClickEye-Service-Key": "other-raw"},
    )

    sa_headers, sa_uid = await _register_and_login(client, "sa@intake.com")
    await _set_role(db_session, sa_uid, "superadmin")
    assert len((await client.get("/api/v1/intake", headers=sa_headers)).json()) == 2

    admin_headers, admin_uid = await _register_and_login(client, "admin@intake.com")
    await _set_role(db_session, admin_uid, "admin", organization_id=org.id)
    rows = (await client.get("/api/v1/intake", headers=admin_headers)).json()
    assert len(rows) == 1
    assert rows[0]["title"] == "쇼핑몰 구축"

    noorg_headers, noorg_uid = await _register_and_login(client, "noorg@intake.com")
    await _set_role(db_session, noorg_uid, "admin")
    assert (await client.get("/api/v1/intake", headers=noorg_headers)).json() == []


# ---------------------------------------------------------------------------
# accept / reject
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_accept_creates_project(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
) -> None:
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    intake_id = resp.json()["intake_id"]

    headers, uid = await _register_and_login(client, "approver@intake.com")
    await _set_role(db_session, uid, "admin", organization_id=org.id)

    accepted = await client.post(f"/api/v1/intake/{intake_id}/accept", headers=headers)
    assert accepted.status_code == 200
    body = accepted.json()
    assert body["status"] == "accepted"
    assert body["project_id"] is not None

    project = await db_session.get(Project, uuid.UUID(body["project_id"]))
    assert project is not None
    assert project.name == "쇼핑몰 구축"
    assert project.project_type == "intake"
    assert project.organization_id == org.id  # 서비스 키 조직 전파
    assert project.owner_id == uuid.UUID(uid)  # 승인자 소유
    assert "회원가입" in (project.requirements_text or "")

    # 재승인 시도 → 409 (pending_review 아님)
    again = await client.post(f"/api/v1/intake/{intake_id}/accept", headers=headers)
    assert again.status_code == 409


@pytest.mark.asyncio
async def test_reject(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
) -> None:
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    intake_id = resp.json()["intake_id"]

    headers, uid = await _register_and_login(client, "rejector@intake.com")
    await _set_role(db_session, uid, "admin", organization_id=org.id)

    rejected = await client.post(
        f"/api/v1/intake/{intake_id}/reject", json={"reason": "예산 미달"}, headers=headers
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    intake = await db_session.get(IntakeRequest, uuid.UUID(intake_id))
    await db_session.refresh(intake)
    assert intake.payload["reject_reason"] == "예산 미달"
    assert intake.project_id is None


# ---------------------------------------------------------------------------
# 서비스 키 관리 (superadmin 전용)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_key_lifecycle_superadmin_only(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
) -> None:
    # admin 은 발급 불가 (403)
    admin_headers, admin_uid = await _register_and_login(client, "keyadmin@intake.com")
    await _set_role(db_session, admin_uid, "admin", organization_id=org.id)
    forbidden = await client.post(
        "/api/v1/intake/service-keys", json={"name": "x"}, headers=admin_headers
    )
    assert forbidden.status_code == 403

    sa_headers, sa_uid = await _register_and_login(client, "keysa@intake.com")
    await _set_role(db_session, sa_uid, "superadmin")

    # 발급: 평문 key 1회 반환 + DB 에는 해시만 저장
    created = await client.post(
        "/api/v1/intake/service-keys",
        json={"name": "파트너A", "organization_id": str(org.id)},
        headers=sa_headers,
    )
    assert created.status_code == 201
    body = created.json()
    plain = body["key"]
    assert plain and plain != body["id"]
    key_row = await db_session.get(IntakeServiceKey, uuid.UUID(body["id"]))
    assert key_row.key_hash == hashlib.sha256(plain.encode()).hexdigest()

    # 발급된 평문 키로 접수 성공
    ok = await client.post(
        "/api/v1/intake",
        json=_structured_body(),
        headers={"X-ClickEye-Service-Key": plain},
    )
    assert ok.status_code == 202

    # 목록: 해시/평문 미노출
    listed = await client.get("/api/v1/intake/service-keys", headers=sa_headers)
    assert listed.status_code == 200
    assert all("key" not in row and "key_hash" not in row for row in listed.json())

    # 비활성화 → 해당 키 인증 401
    deleted = await client.delete(f"/api/v1/intake/service-keys/{body['id']}", headers=sa_headers)
    assert deleted.status_code == 200
    assert deleted.json()["is_active"] is False
    unauthorized = await client.post(
        "/api/v1/intake",
        json=_structured_body(),
        headers={"X-ClickEye-Service-Key": plain},
    )
    assert unauthorized.status_code == 401


# ---------------------------------------------------------------------------
# A3-lite: SSRF 하드닝 (url fetch)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blocked_url",
    ["http://127.0.0.1/x", "http://169.254.169.254/"],
)
async def test_ssrf_blocked_url_still_202(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
    blocked_url: str,
) -> None:
    """사설/메타데이터 IP url → fetch 미수행 + SSRF_BLOCKED 기록, 접수는 202 유지."""
    resp = await client.post(
        "/api/v1/intake",
        json={"input_type": "url", "title": "내부망 시도", "source_url": blocked_url},
        headers=_machine_headers(),
    )
    assert resp.status_code == 202
    intake = await db_session.get(IntakeRequest, uuid.UUID(resp.json()["intake_id"]))
    assert intake.normalized_text is None
    assert "SSRF_BLOCKED" in intake.payload["fetch_error"]


# ---------------------------------------------------------------------------
# A3-lite: callback 상태 푸시 (accept/reject)
# ---------------------------------------------------------------------------


@pytest.fixture
def callback_capture(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    """httpx.AsyncClient.post 를 가로채 외부(콜백) POST 만 캡처한다.

    테스트 앱 호출(base_url http://test, ASGITransport)은 원본으로 위임 —
    콜백 등 그 외 모든 아웃바운드 POST 는 네트워크 없이 캡처된다.
    """
    captured: list[dict] = []
    orig_post = httpx.AsyncClient.post

    async def _fake_post(self: httpx.AsyncClient, url, **kwargs):  # type: ignore[no-untyped-def]
        if str(url).startswith(("http://test/", "/")):  # 테스트 앱(ASGI) 호출은 위임
            return await orig_post(self, url, **kwargs)
        captured.append(
            {
                "url": str(url),
                "headers": dict(kwargs.get("headers") or {}),
                "content": kwargs.get("content"),
            }
        )
        return httpx.Response(200, request=httpx.Request("POST", str(url)))

    monkeypatch.setattr(httpx.AsyncClient, "post", _fake_post)
    return captured


@pytest.fixture
def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    """partner.example.com 등 콜백 호스트 DNS 를 공인 IP 로 고정(오프라인 결정성).

    SSRF 가드(_assert_public_url)는 실제 로직 그대로 타되, 테스트 환경의
    네트워크/DNS 에 의존하지 않도록 해석 결과만 공인 대역으로 응답한다.
    """

    def _fake_getaddrinfo(host, port, *args, **kwargs):  # type: ignore[no-untyped-def]  # noqa: ARG001
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo)


async def _drain_callback_tasks() -> None:
    """fire-and-forget 콜백 태스크가 남아 있으면 완료까지 기다린다."""
    for task in list(intake_service_module._callback_tasks):
        await task


async def _accept_flow(
    client: AsyncClient, db_session: AsyncSession, org: Organization, body: dict, email: str
) -> tuple[str, dict]:
    """접수 → admin 승인까지 수행하고 (intake_id, accept 응답 body)를 반환."""
    resp = await client.post("/api/v1/intake", json=body, headers=_machine_headers())
    intake_id = resp.json()["intake_id"]
    headers, uid = await _register_and_login(client, email)
    await _set_role(db_session, uid, "admin", organization_id=org.id)
    accepted = await client.post(f"/api/v1/intake/{intake_id}/accept", headers=headers)
    assert accepted.status_code == 200
    return intake_id, accepted.json()


@pytest.mark.asyncio
async def test_accept_sends_signed_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
    callback_capture: list[dict],
    public_dns: None,
) -> None:
    """accept 시 callback_url 로 서명된 accepted 페이로드가 POST 된다."""
    intake_id, accept_body = await _accept_flow(
        client, db_session, org, _structured_body(), "cbaccept@intake.com"
    )
    await _drain_callback_tasks()

    assert len(callback_capture) == 1
    sent = callback_capture[0]
    assert sent["url"] == "https://partner.example.com/hook"

    payload = json.loads(sent["content"])
    assert payload["intake_id"] == intake_id
    assert payload["status"] == "accepted"
    assert payload["project_id"] == accept_body["project_id"]
    assert payload["title"] == "쇼핑몰 구축"
    assert payload["timestamp"]

    # 서명: key = sha256(평문 서비스 키) hexdigest, message = 본문 bytes.
    signature = sent["headers"]["X-ClickEye-Signature"]
    secret = hashlib.sha256(RAW_KEY.encode()).hexdigest()
    expected = hmac.new(secret.encode(), sent["content"], hashlib.sha256).hexdigest()
    assert signature == expected


@pytest.mark.asyncio
async def test_reject_sends_rejected_callback(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
    callback_capture: list[dict],
    public_dns: None,
) -> None:
    """reject 시 status=rejected(project_id 없음) 페이로드가 POST 된다."""
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    intake_id = resp.json()["intake_id"]
    headers, uid = await _register_and_login(client, "cbreject@intake.com")
    await _set_role(db_session, uid, "admin", organization_id=org.id)
    rejected = await client.post(
        f"/api/v1/intake/{intake_id}/reject", json={"reason": "범위 초과"}, headers=headers
    )
    assert rejected.status_code == 200
    await _drain_callback_tasks()

    assert len(callback_capture) == 1
    payload = json.loads(callback_capture[0]["content"])
    assert payload["intake_id"] == intake_id
    assert payload["status"] == "rejected"
    assert payload["project_id"] is None
    assert "X-ClickEye-Signature" in callback_capture[0]["headers"]


# ---------------------------------------------------------------------------
# A3-full: metaprompt 정제 연동 (머신 pending 조회 / refined 제출 / accept 우선순위)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_response_exposes_refine_fields(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
) -> None:
    """검토 콘솔 응답에 refined_text/refine_status 가 노출된다(초기 pending/None)."""
    await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    sa_headers, sa_uid = await _register_and_login(client, "refinefields@intake.com")
    await _set_role(db_session, sa_uid, "superadmin")
    rows = (await client.get("/api/v1/intake", headers=sa_headers)).json()
    assert rows[0]["refine_status"] == "pending"
    assert rows[0]["refined_text"] is None


@pytest.mark.asyncio
async def test_refine_pending_machine_list_requires_token(
    client: AsyncClient,
    intake_enabled: None,
    service_key: IntakeServiceKey,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """토큰 설정 시 헤더 필수(401), 일치하면 200 — verify_governance_token 재사용."""
    await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    monkeypatch.setattr(settings, "governance_service_token", "refine-token")

    no_token = await client.get("/api/v1/intake/refine/pending")
    assert no_token.status_code == 401

    ok = await client.get(
        "/api/v1/intake/refine/pending",
        headers={"X-Governance-Token": "refine-token"},
    )
    assert ok.status_code == 200
    items = ok.json()
    assert len(items) == 1
    item = items[0]
    assert set(item) == {"id", "title", "input_type", "normalized_text", "target", "priority"}
    assert item["title"] == "쇼핑몰 구축"
    assert "회원가입" in item["normalized_text"]


@pytest.mark.asyncio
async def test_submit_refined_transitions_and_leaves_pending_list(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    service_key: IntakeServiceKey,
) -> None:
    """refined 제출 → refine_status=refined 저장 + pending 목록에서 제외된다."""
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    intake_id = resp.json()["intake_id"]

    submitted = await client.post(
        f"/api/v1/intake/{intake_id}/refined",
        json={"refined_text": "## 목표\n정제된 구현 스펙"},
    )
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["refine_status"] == "refined"
    assert body["refined_text"] == "## 목표\n정제된 구현 스펙"
    assert body["status"] == "pending_review"  # 검토 게이트는 그대로

    pending = (await client.get("/api/v1/intake/refine/pending")).json()
    assert pending == []


@pytest.mark.asyncio
async def test_submit_empty_refined_marks_skipped(
    client: AsyncClient,
    intake_enabled: None,
    service_key: IntakeServiceKey,
) -> None:
    """공백만 제출 → refined_text 미저장(None) + skipped (다음 배치 재선택 제외)."""
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    intake_id = resp.json()["intake_id"]

    submitted = await client.post(
        f"/api/v1/intake/{intake_id}/refined", json={"refined_text": "   \n\t "}
    )
    assert submitted.status_code == 200
    assert submitted.json()["refine_status"] == "skipped"
    assert submitted.json()["refined_text"] is None
    assert (await client.get("/api/v1/intake/refine/pending")).json() == []


@pytest.mark.asyncio
async def test_accept_prefers_refined_text(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
) -> None:
    """accept 는 refined_text 를 Project.requirements_text 로 우선 사용한다."""
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    intake_id = resp.json()["intake_id"]
    refined = "## 목표\n쇼핑몰 구축 구현 스펙 (정제본)"
    await client.post(f"/api/v1/intake/{intake_id}/refined", json={"refined_text": refined})

    headers, uid = await _register_and_login(client, "refinedaccept@intake.com")
    await _set_role(db_session, uid, "admin", organization_id=org.id)
    accepted = await client.post(f"/api/v1/intake/{intake_id}/accept", headers=headers)
    assert accepted.status_code == 200

    project = await db_session.get(Project, uuid.UUID(accepted.json()["project_id"]))
    assert project.requirements_text == refined  # normalized_text 아님


@pytest.mark.asyncio
async def test_submit_refined_non_pending_409(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
) -> None:
    """accepted 등 pending_review 아닌 건에 refined 제출 → 409."""
    resp = await client.post("/api/v1/intake", json=_structured_body(), headers=_machine_headers())
    intake_id = resp.json()["intake_id"]
    headers, uid = await _register_and_login(client, "refined409@intake.com")
    await _set_role(db_session, uid, "admin", organization_id=org.id)
    assert (
        await client.post(f"/api/v1/intake/{intake_id}/accept", headers=headers)
    ).status_code == 200

    conflict = await client.post(
        f"/api/v1/intake/{intake_id}/refined", json={"refined_text": "늦은 정제"}
    )
    assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_callback_private_ip_skipped(
    client: AsyncClient,
    db_session: AsyncSession,
    intake_enabled: None,
    org: Organization,
    service_key: IntakeServiceKey,
    callback_capture: list[dict],
) -> None:
    """콜백 URL 이 사설 IP 면 SSRF 가드로 발송 자체를 스킵한다(POST 미발생)."""
    body = {**_structured_body(title="내부망 콜백"), "callback_url": "http://127.0.0.1/hook"}
    await _accept_flow(client, db_session, org, body, "cbprivate@intake.com")
    await _drain_callback_tasks()
    assert callback_capture == []
