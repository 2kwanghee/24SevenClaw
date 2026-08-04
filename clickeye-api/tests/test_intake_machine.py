"""머신 조회 엔드포인트 테스트 (다프로젝트화 P5/F-4).

GET /intake/machine/projects — 서비스 키 조직의 인테이크 유래 프로젝트 목록.
핵심 검증:
- 기계 인증 성공: 목록 형태·필드·ticket_prefix 규약, project_id 없는 건 제외
- 무키 401
- 타 조직 격리(다른 조직 키로는 안 보임)
"""

from __future__ import annotations

import hashlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.intake import IntakeRequest, IntakeServiceKey
from app.models.organization import Organization
from app.models.project import Project

RAW_KEY_A = "machine-key-org-a-plaintext"
RAW_KEY_B = "machine-key-org-b-plaintext"


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest.fixture
def intake_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """feature_intake 킬스위치 활성화(없으면 전 라우트 404)."""
    monkeypatch.setattr(settings, "feature_intake", True)


async def _make_org(db: AsyncSession, name: str) -> Organization:
    org = Organization(company_name=name)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def _make_key(db: AsyncSession, raw: str, org: Organization) -> IntakeServiceKey:
    key = IntakeServiceKey(name="외부수주서비스", key_hash=_hash(raw), organization_id=org.id)
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


async def _register_owner(client: AsyncClient) -> uuid.UUID:
    """Project.owner_id 용 사용자 1명을 API 로 등록하고 id 를 반환한다."""
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pw12345678", "display_name": "owner"},
    )
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "pw12345678"})
    token = resp.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return uuid.UUID(me.json()["id"])


async def _seed_intake_with_project(
    db: AsyncSession,
    key: IntakeServiceKey,
    owner_id: uuid.UUID,
    org: Organization,
    title: str,
    tickets_status: str = "none",
) -> IntakeRequest:
    project = Project(
        owner_id=owner_id,
        name=title,
        slug=f"slug-{uuid.uuid4().hex[:8]}",
        organization_id=org.id,
        project_type="intake",
    )
    db.add(project)
    await db.flush()
    intake = IntakeRequest(
        service_key_id=key.id,
        input_type="structured",
        title=title,
        payload={},
        status="accepted",
        project_id=project.id,
        tickets_status=tickets_status,
    )
    db.add(intake)
    await db.commit()
    await db.refresh(intake)
    return intake


async def _seed_intake_no_project(
    db: AsyncSession, key: IntakeServiceKey, title: str
) -> IntakeRequest:
    intake = IntakeRequest(
        service_key_id=key.id,
        input_type="structured",
        title=title,
        payload={},
        status="pending_review",
    )
    db.add(intake)
    await db.commit()
    await db.refresh(intake)
    return intake


@pytest.mark.asyncio
async def test_machine_projects_success(
    client: AsyncClient, db_session: AsyncSession, intake_enabled: None
) -> None:
    """기계 인증 성공 — 목록·필드·ticket_prefix 규약, project_id 없는 건 제외."""
    org_a = await _make_org(db_session, "고객사A")
    key_a = await _make_key(db_session, RAW_KEY_A, org_a)
    owner = await _register_owner(client)
    it1 = await _seed_intake_with_project(
        db_session, key_a, owner, org_a, "프로젝트1", tickets_status="issued"
    )
    it2 = await _seed_intake_with_project(db_session, key_a, owner, org_a, "프로젝트2")
    # project_id 없는 인테이크 — 목록에서 제외되어야 한다.
    await _seed_intake_no_project(db_session, key_a, "미생성인테이크")

    resp = await client.get(
        "/api/v1/intake/machine/projects", headers={"X-ClickEye-Service-Key": RAW_KEY_A}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2  # project_id 없는 건은 제외

    by_id = {item["intake_id"]: item for item in data}
    assert str(it1.id) in by_id and str(it2.id) in by_id
    for item in data:
        assert set(item) >= {
            "intake_id",
            "project_id",
            "title",
            "tickets_status",
            "ticket_prefix",
        }
        assert item["project_id"] is not None
    # ticket_prefix 는 intake_issue.sh 규약(`[수주:<intake_id 앞 8자>] `)을 서버가 재현한다.
    assert by_id[str(it1.id)]["ticket_prefix"] == f"[수주:{str(it1.id)[:8]}] "
    assert by_id[str(it1.id)]["tickets_status"] == "issued"


@pytest.mark.asyncio
async def test_machine_projects_requires_key(client: AsyncClient, intake_enabled: None) -> None:
    """무키 → 401 (POST /intake 와 동일한 머신 인증 계약)."""
    resp = await client.get("/api/v1/intake/machine/projects")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_machine_projects_org_isolation(
    client: AsyncClient, db_session: AsyncSession, intake_enabled: None
) -> None:
    """타 조직 격리 — 다른 조직 서비스 키로는 A 조직 프로젝트가 보이지 않는다."""
    org_a = await _make_org(db_session, "고객사A")
    org_b = await _make_org(db_session, "고객사B")
    key_a = await _make_key(db_session, RAW_KEY_A, org_a)
    await _make_key(db_session, RAW_KEY_B, org_b)
    owner = await _register_owner(client)
    it_a = await _seed_intake_with_project(db_session, key_a, owner, org_a, "A프로젝트")

    resp = await client.get(
        "/api/v1/intake/machine/projects", headers={"X-ClickEye-Service-Key": RAW_KEY_B}
    )
    assert resp.status_code == 200
    ids = {item["intake_id"] for item in resp.json()}
    assert str(it_a.id) not in ids
