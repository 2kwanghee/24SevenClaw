"""DeliveryProfile 정책 주입(다프로젝트화 P0) — 모델 + HTTP 어댑터 테스트.

핵심 수용기준:
- project_id 미지정 → 기존과 동일 판정(하위호환, policy_source 키조차 없음)
- 프로파일 주입 → 커스텀 정책이 실제 판정을 바꿈(Java 경로가 계약면으로 잡혀 drift 차단)
- 프로파일 토글이 **서버 env 를 무시**(static — env 로 CONTRACT=off 를 줘도 프로파일 기준)
- 불량 policy JSON → 422(기본 정책으로 조용히 폴백하지 않음, fail-closed)
- 미등록 project_id → 기본 정책 폴백 + policy_source 로 그 사실이 응답에 드러남
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.delivery_profile import DeliveryProfile
from app.models.project import Project

# infraeye3 형태의 타 프로젝트 정책 — 계약면이 Java 경로이고 스펙 경로도 다르다.
_JAVA_POLICY: dict = {
    "contract_surface_prefixes": ["src/main/java/"],
    "openapi_spec": "docs/api/openapi.json",
    "generated_client_prefix": "src/generated/",
    "contracts_prefix": "contracts/",
    "high_prefixes": ["infra/"],
}

# ClickEye 정책에서는 계약면이 아니지만 위 정책에서는 계약면인 파일.
_JAVA_SURFACE_FILE = "src/main/java/com/example/ApiController.java"


@pytest.fixture(autouse=True)
def _clear_toggles(monkeypatch):
    """테스트 격리: FLOWOPS_GOVERNANCE* 환경변수를 초기화(기본 상태로)."""
    for k in list(os.environ):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            monkeypatch.delenv(k, raising=False)
    yield


async def _seed_project(db: AsyncSession) -> Project:
    proj = Project(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        name="타 프로젝트",
        slug=f"other-{uuid.uuid4().hex[:8]}",
        status="active",
        settings={},
    )
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return proj


async def _seed_profile(db: AsyncSession, policy: dict, *, tier: str = "standard") -> Project:
    """프로젝트 + 딜리버리 프로파일을 시딩하고 프로젝트를 반환한다."""
    proj = await _seed_project(db)
    db.add(DeliveryProfile(id=uuid.uuid4(), project_id=proj.id, tier=tier, policy=policy))
    await db.commit()
    return proj


# ── 모델 기본값 ──────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_model_defaults(db_session: AsyncSession):
    proj = await _seed_project(db_session)
    profile = DeliveryProfile(id=uuid.uuid4(), project_id=proj.id)
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    assert profile.tier == "lite"
    assert profile.policy == {}
    # locked 는 P0 에서 집행하지 않는 표시용 플래그 — 기본 False.
    assert profile.locked is False
    assert profile.updated_by is None


# ── (1) project_id 미지정 → 기존 동작 그대로 ─────────────────────────────────
@pytest.mark.asyncio
async def test_evaluate_without_project_id_unchanged(client):
    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": "ralph/CE-1", "files": [_JAVA_SURFACE_FILE]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Java 경로는 ClickEye 계약면이 아니므로 drift 없음 → 기존 판정.
    assert body["verdict"] == "pass" and body["merge_decision"] == "direct"
    assert body["checks"]["contract_drift"]["status"] == "pass"
    # 정책 미주입 경로에는 신규 키가 새지 않는다(응답 바이트 불변).
    assert "policy_source" not in body


@pytest.mark.asyncio
async def test_evaluate_without_project_id_equals_kernel(client):
    """HTTP(정책 미주입) == 커널 기본 정책 판정(회귀 0의 직접 증거)."""
    from governance.core import evaluate as kernel_evaluate

    files = ["clickeye-api/app/api/v1/governance.py"]
    expected = kernel_evaluate("main", "ralph/CE-1", files=files, project_dir=None)
    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": "ralph/CE-1", "files": files},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in ("verdict", "merge_decision", "tier", "failures", "issue_key"):
        assert body[key] == expected[key], key


# ── (2) 프로파일 주입 → 판정이 실제로 바뀐다 ──────────────────────────────────
@pytest.mark.asyncio
async def test_profile_policy_changes_verdict(client, db_session):
    proj = await _seed_profile(db_session, _JAVA_POLICY)

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE],
            "project_id": str(proj.id),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["policy_source"] == "project_profile"
    # Java 경로가 계약면으로 잡히고 openapi 동반이 없음 → drift 차단.
    assert body["checks"]["contract_drift"]["status"] == "fail"
    assert body["verdict"] == "fail" and body["merge_decision"] == "block"


@pytest.mark.asyncio
async def test_profile_policy_passes_when_spec_accompanies(client, db_session):
    """같은 정책에서 프로파일이 지정한 스펙 경로가 동반되면 통과(정책이 정본임을 확인)."""
    proj = await _seed_profile(db_session, _JAVA_POLICY)

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE, "docs/api/openapi.json"],
            "project_id": str(proj.id),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["checks"]["contract_drift"]["status"] == "pass"
    assert body["verdict"] == "pass"


@pytest.mark.asyncio
async def test_profile_high_risk_prefix_demotes_to_pr(client, db_session):
    """고위험 경로도 프로파일이 정한다 — infra/ 변경이 HIGH → 직접머지 금지(pr 강등)."""
    proj = await _seed_profile(db_session, _JAVA_POLICY)

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": ["infra/docker-compose.yml"],
            "project_id": str(proj.id),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tier"] == "HIGH"
    assert body["merge_decision"] == "pr"


# ── (3) 프로파일 토글은 서버 env 를 무시한다(static) ──────────────────────────
@pytest.mark.asyncio
async def test_profile_ignores_server_env_contract_off(client, db_session, monkeypatch):
    """env CONTRACT=false 여도 프로파일 기준(미지정=on)으로 판정 → 여전히 차단."""
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "false")
    proj = await _seed_profile(db_session, _JAVA_POLICY)

    # 대조군: 정책 미주입이면 env 가 정본 → contract_drift skip.
    baseline = await client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": "ralph/CE-1", "files": [_JAVA_SURFACE_FILE]},
    )
    assert baseline.json()["checks"]["contract_drift"]["status"] == "skip"

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE],
            "project_id": str(proj.id),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["checks"]["contract_drift"]["status"] == "fail", body["checks"]
    assert body["verdict"] == "fail"


@pytest.mark.asyncio
async def test_profile_ignores_server_env_master_off(client, db_session, monkeypatch):
    """env 마스터 off 여도 프로파일 기준으로 거버넌스가 살아있다(서버 env 로 우회 불가)."""
    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "off")
    proj = await _seed_profile(db_session, _JAVA_POLICY)

    baseline = await client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": "ralph/CE-1", "files": [_JAVA_SURFACE_FILE]},
    )
    assert baseline.json()["governance"] == "off"

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE],
            "project_id": str(proj.id),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["governance"] == "on"
    assert body["verdict"] == "fail"


@pytest.mark.asyncio
async def test_profile_toggle_off_beats_unset_env(client, db_session):
    """반대 방향도 성립: 프로파일이 CONTRACT=false 면 env 미설정(=on)이어도 skip."""
    policy = dict(_JAVA_POLICY, toggles={"FLOWOPS_GOVERNANCE_CONTRACT": False})
    proj = await _seed_profile(db_session, policy)

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE],
            "project_id": str(proj.id),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["checks"]["contract_drift"]["status"] == "skip"
    assert body["verdict"] == "pass"


# ── (4) 불량 policy JSON → 422 (조용한 폴백 금지) ─────────────────────────────
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_policy",
    [
        {"contract_surface_prefixes": "src/main/java/"},  # 배열이어야 함
        {"high_path_patterns": ["("]},  # 정규식 컴파일 실패
        {"toggles": {"FLOWOPS_GOVERNANCE_CONTRACT": "maybe"}},  # 불리언 해석 불가
        {"오타키": True},  # 알 수 없는 키(조용한 무시 금지)
    ],
)
async def test_invalid_policy_returns_422(client, db_session, bad_policy):
    proj = await _seed_profile(db_session, bad_policy)

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE],
            "project_id": str(proj.id),
        },
    )
    # 기본 정책으로 폴백해 200 을 주면 안 된다(fail-closed).
    assert resp.status_code == 422, resp.text
    detail = resp.json()["detail"]
    assert "DeliveryProfile.policy" in detail  # 사유가 담겨야 한다


# ── (5) 미등록 project_id → 기본 정책 폴백 + 그 사실 노출 ─────────────────────
@pytest.mark.asyncio
async def test_unregistered_project_falls_back_and_discloses(client, db_session):
    proj = await _seed_project(db_session)  # 프로파일 없음

    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE],
            "project_id": str(proj.id),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 조용한 폴백 금지 — 응답에 폴백 사실이 드러난다.
    assert body["policy_source"] == "default_no_profile"
    # 판정 자체는 기본 정책 = 기존과 동일.
    assert body["checks"]["contract_drift"]["status"] == "pass"
    assert body["verdict"] == "pass" and body["merge_decision"] == "direct"


@pytest.mark.asyncio
async def test_nonexistent_project_id_falls_back(client):
    """존재하지 않는 프로젝트 UUID 도 동일하게 폴백 + 노출(404 로 만들지 않는다 — 게이트는
    머지 판정이 본업이며 프로젝트 등록 여부로 파이프라인을 세우지 않는다)."""
    resp = await client.post(
        "/api/v1/governance/evaluate",
        json={
            "base": "main",
            "head": "ralph/CE-1",
            "files": [_JAVA_SURFACE_FILE],
            "project_id": str(uuid.uuid4()),
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["policy_source"] == "default_no_profile"


# ── (6) GET /policy 의 project_id 선택 파라미터 ───────────────────────────────
@pytest.mark.asyncio
async def test_get_policy_without_project_id_unchanged(client, auth_headers):
    resp = await client.get("/api/v1/governance/policy", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 기존 키셋 불변(신규 키가 null 로 새지 않음).
    assert "policy_source" not in body
    # `.github/**` 는 CE-375 에서 HIGH 로 추가됐다(워크플로 셸 주입 → PR 경로 강등).
    assert body["high_risk"]["prefixes"] == [
        "clickeye-contracts/",
        "clickeye-infra/",
        ".github/workflows/",
        ".github/actions/",
    ]
    assert "API 서버 env" in body["source_note"]


@pytest.mark.asyncio
async def test_get_policy_with_project_id_returns_project_policy(client, auth_headers, db_session):
    proj = await _seed_profile(db_session, _JAVA_POLICY)

    resp = await client.get(f"/api/v1/governance/policy?project_id={proj.id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["policy_source"] == "project_profile"
    # 고위험 경로가 프로젝트 정책 기준으로 노출된다.
    assert body["high_risk"]["prefixes"] == ["infra/"]
    # source_note 가 env 미조회(static)임을 밝힌다.
    assert "DeliveryProfile" in body["source_note"]


@pytest.mark.asyncio
async def test_get_policy_project_toggles_ignore_env(client, auth_headers, db_session, monkeypatch):
    """env 마스터 off 여도 프로젝트 정책 요약은 프로파일 기준(on)으로 보고한다."""
    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "off")
    proj = await _seed_profile(db_session, _JAVA_POLICY)

    resp = await client.get(f"/api/v1/governance/policy?project_id={proj.id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["governance_enabled"] is True
    assert body["toggles"]["FLOWOPS_GOVERNANCE"] is True


@pytest.mark.asyncio
async def test_get_policy_unregistered_project_discloses_fallback(client, auth_headers, db_session):
    proj = await _seed_project(db_session)
    resp = await client.get(f"/api/v1/governance/policy?project_id={proj.id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["policy_source"] == "default_no_profile"


@pytest.mark.asyncio
async def test_get_policy_invalid_profile_returns_422(client, auth_headers, db_session):
    proj = await _seed_profile(db_session, {"high_prefixes": [""]})  # 빈 문자열 원소 → 불량
    resp = await client.get(f"/api/v1/governance/policy?project_id={proj.id}", headers=auth_headers)
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_get_policy_requires_auth(client, db_session):
    """project_id 를 줘도 인증 요구는 그대로(신규 우회 경로 없음)."""
    proj = await _seed_profile(db_session, _JAVA_POLICY)
    resp = await client.get(f"/api/v1/governance/policy?project_id={proj.id}")
    assert resp.status_code in (401, 403), resp.text


# ── 서비스 계층: DB 미주입 시 폴백도 노출된다 ─────────────────────────────────
@pytest.mark.asyncio
async def test_service_without_db_discloses_no_db():
    from app.schemas.governance import GovernanceEvaluateRequest
    from app.services.governance_gate_service import GovernanceGateService

    req = GovernanceEvaluateRequest(
        head="ralph/CE-1", files=[_JAVA_SURFACE_FILE], project_id=uuid.uuid4()
    )
    result = await GovernanceGateService().evaluate(req)
    assert result["policy_source"] == "default_no_db"
    assert result["verdict"] == "pass"  # 기본 정책 판정
