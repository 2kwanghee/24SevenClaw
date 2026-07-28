"""제어면 수신(서비스+엔드포인트) 테스트 (다프로젝트화 P2, D-14).

검증 축:
  1. 수리 경로 — 유효 YAML → DeliveryProfile 미러 upsert(원문·해시·버전·provenance·
     policy 지정분) + 재제출 시 갱신(프로젝트당 1행 유지).
  2. 판정 연동 — 제출된 policy 가 실제로 governance evaluate 판정을 바꾼다
     (미러가 죽은 데이터가 아님을 증명).
  3. fail-closed — 불량 YAML 422 + 기계 소비형 거부(ControlPlaneRejection 형태:
     code/reasons/schema_supported). 이 body 가 서비스 #2 콜백 계약이다.
  4. 인증 — X-ClickEye-Service-Key 없음/무효 → 401 (인테이크와 동일 체계 재사용).
  5. 원문 정본 — load_control_plane 이 source_yaml 재검증으로 전체 제어면을 복원.

Usage:
    cd clickeye-api && uv run pytest tests/test_control_plane_service.py -v
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.delivery_profile import DeliveryProfile
from app.models.project import Project
from app.models.user import User
from app.services.control_plane_service import ControlPlaneService
from app.services.intake_service import IntakeService

VALID_YAML = """\
schema_version: "1.0"
tier: enterprise
provenance:
  template_id: legacy-modernize-v2
  generated_by: service-2
policy:
  contract_surface_prefixes: ["backend/src/main/java/"]
  openapi_spec: "contracts/openapi.yaml"
  high_prefixes: ["db/migration/"]
  issue_key_shape: "^(TASK|CYCLE)-[A-Z0-9]+-\\\\d+$"
  issue_key_search: "(TASK|CYCLE)-[A-Z0-9]+-\\\\d+"
retry_limits:
  ticket_retries: 5
gates:
  check: ["./gradlew check"]
"""


@pytest.fixture
async def project(db_session) -> Project:
    owner = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4().hex[:8]}@test.io",
        password_hash="x",
        display_name="소유자",
        is_active=True,
    )
    db_session.add(owner)
    prj = Project(
        id=uuid.uuid4(), owner_id=owner.id, name="인프라 현대화", slug=f"p-{uuid.uuid4().hex[:8]}"
    )
    db_session.add(prj)
    await db_session.commit()
    return prj


@pytest.fixture
async def service_key(db_session) -> str:
    """서비스 #2 머신 키 — 평문은 발급 시 1회만 노출되는 실제 계약과 동일 경로로 생성."""
    raw, _ = await IntakeService(db_session).create_service_key("service-2", None)
    return raw


# ── 1. 수리 경로(서비스 계층) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_upserts_mirror_with_provenance(db_session, project) -> None:
    svc = ControlPlaneService(db_session)
    profile, plane = await svc.submit(project_id=project.id, control_yaml=VALID_YAML)

    assert profile.tier == "enterprise"
    assert profile.schema_version == "1.0"
    assert str(profile.source_signature).startswith("sha256:")
    assert profile.source_yaml == VALID_YAML                    # 원문 그대로 보존
    assert profile.provenance["template_id"] == "legacy-modernize-v2"
    # policy 컬럼은 지정분만(미러 오염 방지) — 전체 Policy 직렬화가 아니다
    assert set(profile.policy.keys()) == {
        "contract_surface_prefixes",
        "openapi_spec",
        "high_prefixes",
        "issue_key_shape",
        "issue_key_search",
    }
    assert profile.updated_by is None                           # 기계 수신 — 출처는 서명이 말한다
    # 전체 제어면은 검증 결과(plane)로 반환된다
    assert plane.retry_limits["ticket_retries"] == 5


@pytest.mark.asyncio
async def test_resubmit_updates_single_row(db_session, project) -> None:
    """재제출은 새 행이 아니라 갱신 — 프로젝트당 미러 1행(unique) 유지."""
    svc = ControlPlaneService(db_session)
    p1, _ = await svc.submit(project_id=project.id, control_yaml=VALID_YAML)
    updated = VALID_YAML.replace("tier: enterprise", "tier: standard")
    p2, _ = await svc.submit(project_id=project.id, control_yaml=updated)

    assert p1.id == p2.id
    assert p2.tier == "standard"
    assert p2.source_signature != p1.source_signature or p2.source_yaml == updated
    rows = (
        (await db_session.execute(
            select(DeliveryProfile).where(DeliveryProfile.project_id == project.id)
        )).scalars().all()
    )
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_submit_unknown_project_404_before_any_write(db_session) -> None:
    from app.core.exceptions import AppError

    with pytest.raises(AppError) as ei:
        await ControlPlaneService(db_session).submit(
            project_id=uuid.uuid4(), control_yaml=VALID_YAML
        )
    assert ei.value.status_code == 404


# ── 2. 판정 연동 — 미러가 실제 판정을 바꾼다 ─────────────────────────────────


@pytest.mark.asyncio
async def test_submitted_policy_changes_governance_verdict(db_session, project) -> None:
    """제출된 정책으로 evaluate 하면 Java 경로가 계약면으로 잡혀 drift 차단.

    이 테스트가 없으면 미러는 '저장은 되지만 아무도 읽지 않는' 죽은 데이터일 수 있다.
    """
    from app.schemas.governance import GovernanceEvaluateRequest
    from app.services.governance_gate_service import GovernanceGateService

    await ControlPlaneService(db_session).submit(project_id=project.id, control_yaml=VALID_YAML)

    result = await GovernanceGateService(db_session).evaluate(
        GovernanceEvaluateRequest(
            head="ralph/TASK-GATE-001",
            files=["backend/src/main/java/com/x/DeviceController.java"],
            project_id=project.id,
        )
    )
    assert result["policy_source"] == "project_profile"
    assert result["checks"]["contract_drift"]["status"] == "fail"   # 스펙 미동반 → 차단
    assert result["checks"]["ticket_ref"]["status"] == "pass"       # 커스텀 키 형태 통과
    assert result["merge_decision"] == "block"


# ── 3~4. 엔드포인트 — 인증·수리·거부 계약 ────────────────────────────────────


@pytest.mark.asyncio
async def test_endpoint_requires_service_key(client: AsyncClient, project) -> None:
    resp = await client.put(
        "/api/v1/governance/control-plane",
        json={"project_id": str(project.id), "control_yaml": VALID_YAML},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_rejects_invalid_service_key(client: AsyncClient, project) -> None:
    resp = await client.put(
        "/api/v1/governance/control-plane",
        json={"project_id": str(project.id), "control_yaml": VALID_YAML},
        headers={"X-ClickEye-Service-Key": "wrong-key"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_endpoint_accepts_valid_yaml(client: AsyncClient, project, service_key) -> None:
    resp = await client.put(
        "/api/v1/governance/control-plane",
        json={"project_id": str(project.id), "control_yaml": VALID_YAML},
        headers={"X-ClickEye-Service-Key": service_key},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["schema_version"] == "1.0"
    assert body["tier"] == "enterprise"
    assert body["source_signature"].startswith("sha256:")
    # effective 는 병합·기본값 승계가 끝난 유효 제어면 — 표준 정지조건이 포함돼 있어야 한다
    assert "cost_incurring_operation" in body["effective"]["auto_stop_conditions"]
    assert body["effective"]["retry_limits"]["ticket_retries"] == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_yaml,fragment",
    [
        ("schema_version: '1.0'\noops: 1", "알 수 없는 키"),           # 최상위 오타
        ("schema_version: '9.9'", "미지원 버전"),                      # 버전 협상 실패
        ("tier: lite", "schema_version"),                              # 필수 절 누락
        ("schema_version: '1.0'\npolicy:\n  typo_key: 1", "policy"),   # 판정면 위임 오류
        (":: not yaml ::", "YAML 파싱 실패"),                          # 파싱 불가
    ],
)
async def test_endpoint_rejection_is_machine_consumable(
    client: AsyncClient, project, service_key, bad_yaml, fragment
) -> None:
    """422 거부 body 가 서비스 #2 콜백 계약(code/reasons/schema_supported)을 지킨다."""
    resp = await client.put(
        "/api/v1/governance/control-plane",
        json={"project_id": str(project.id), "control_yaml": bad_yaml},
        headers={"X-ClickEye-Service-Key": service_key},
    )
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert detail["code"] == "CONTROL_PLANE_INVALID"
    assert any(fragment in r for r in detail["reasons"]), detail["reasons"]
    assert detail["schema_supported"] == ["1.0"]                # 버전 협상 힌트


@pytest.mark.asyncio
async def test_endpoint_unknown_project_404_with_rejection_body(
    client: AsyncClient, service_key
) -> None:
    resp = await client.put(
        "/api/v1/governance/control-plane",
        json={"project_id": str(uuid.uuid4()), "control_yaml": VALID_YAML},
        headers={"X-ClickEye-Service-Key": service_key},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "PROJECT_NOT_FOUND"


# ── 5. 원문 정본 — 재검증 복원 ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_control_plane_restores_from_source_yaml(db_session, project) -> None:
    svc = ControlPlaneService(db_session)
    await svc.submit(project_id=project.id, control_yaml=VALID_YAML)

    plane = await svc.load_control_plane(project.id)
    assert plane is not None
    assert plane.tier == "enterprise"
    assert plane.retry_limits["ticket_retries"] == 5
    assert plane.gates["check"] == ("./gradlew check",)
    # 표준 정지조건은 저장·복원을 거쳐도 축소되지 않는다
    assert "governance_violation" in plane.auto_stop_conditions


@pytest.mark.asyncio
async def test_load_control_plane_none_when_absent(db_session, project) -> None:
    assert await ControlPlaneService(db_session).load_control_plane(project.id) is None
