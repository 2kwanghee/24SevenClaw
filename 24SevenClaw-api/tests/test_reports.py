"""프로젝트 리포트 API 테스트."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.artifact import Artifact
from app.models.orchestrator import OrchestratorSession, PhaseEvent, SubTask
from app.models.user import User


@pytest.fixture
async def project_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    """테스트용 프로젝트 생성 후 ID 반환."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "리포트 테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# === 리포트 조회 테스트 ===


@pytest.mark.asyncio
async def test_get_project_report_empty(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """산출물/세션이 없는 프로젝트 리포트 → 빈 데이터로 정상 반환."""
    resp = await client.get(
        f"/api/v1/reports/project/{project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == project_id
    assert body["project_name"] == "리포트 테스트 프로젝트"
    assert body["project_status"] == "active"
    assert len(body["artifact_status_counts"]) == 7  # 모든 상태 포함
    assert all(c["count"] == 0 for c in body["artifact_status_counts"])
    assert body["phase_timeline"] == []
    assert body["quality_metrics"]["total_artifacts"] == 0
    assert body["quality_metrics"]["released_artifacts"] == 0
    assert body["quality_metrics"]["avg_revision_count"] == 0.0
    assert body["ai_team_activities"] == []
    assert body["sessions_total"] == 0
    assert body["subtasks_total"] == 0
    assert "generated_at" in body


@pytest.mark.asyncio
async def test_get_project_report_with_artifacts(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """산출물이 있는 프로젝트 리포트 → 상태별 카운트 반영."""
    # 산출물 2개 생성
    for name in ["문서 산출물", "코드 산출물"]:
        resp = await client.post(
            f"/api/v1/artifacts/projects/{project_id}/artifacts",
            json={"name": name, "artifact_type": "code", "created_by_ai": "claude"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    # 리포트 조회
    resp = await client.get(
        f"/api/v1/reports/project/{project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    draft_count = next(
        c for c in body["artifact_status_counts"] if c["status"] == "draft"
    )
    assert draft_count["count"] == 2
    assert body["quality_metrics"]["total_artifacts"] == 2
    assert body["quality_metrics"]["released_artifacts"] == 0


@pytest.mark.asyncio
async def test_get_project_report_no_auth(
    client: AsyncClient, project_id: str
) -> None:
    """인증 없이 리포트 조회 → 401/403."""
    resp = await client.get(f"/api/v1/reports/project/{project_id}")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_project_report_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 프로젝트 리포트 조회 → 404."""
    resp = await client.get(
        "/api/v1/reports/project/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_project_report_with_orchestrator(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """오케스트레이터 세션이 있는 프로젝트 → sessions_total 반영."""
    # 세션 생성
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "테스트 세션", "description": "설명"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # 리포트 조회
    resp = await client.get(
        f"/api/v1/reports/project/{project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sessions_total"] == 1


# === KPI 엔드포인트 테스트 ===


@pytest.mark.asyncio
async def test_get_project_kpi_empty(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """데이터 없는 프로젝트 KPI → 빈/0 값 반환."""
    resp = await client.get(
        f"/api/v1/reports/projects/{project_id}/kpi",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == project_id
    assert body["avg_phase_duration"] == []
    assert body["throughput_per_week"] == []
    assert body["automation_rate"] == 0.0
    assert body["review_acceptance_rate"] == 0.0
    assert "generated_at" in body


@pytest.mark.asyncio
async def test_get_project_kpi_with_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
    db_session: AsyncSession,
) -> None:
    """데이터가 있는 프로젝트 KPI → 메트릭 계산 반영."""
    pid = UUID(project_id)
    now = datetime.now(UTC)

    # 오케스트레이터 세션 생성
    session = OrchestratorSession(
        project_id=pid, title="KPI 테스트 세션", phase="designing"
    )
    db_session.add(session)
    await db_session.flush()

    # PhaseEvent: requested(2시간 전) → designing(1시간 전) → duration=3600초
    pe1 = PhaseEvent(
        session_id=session.id,
        old_phase=None,
        new_phase="requested",
        actor_type="agent",
        created_at=now - timedelta(hours=2),
    )
    pe2 = PhaseEvent(
        session_id=session.id,
        old_phase="requested",
        new_phase="designing",
        actor_type="agent",
        created_at=now - timedelta(hours=1),
    )
    db_session.add_all([pe1, pe2])

    # SubTask: 완료 2개, 대기 1개 → automation_rate = 66.7%
    for i, st_status in enumerate(["completed", "completed", "pending"]):
        st = SubTask(
            session_id=session.id,
            title=f"태스크 {i}",
            assigned_role="developer",
            status=st_status,
            order_index=i,
            updated_at=now - timedelta(days=i),
        )
        db_session.add(st)

    # Artifact: reviewed(수정0) + released(수정2) → acceptance=50%
    a1 = Artifact(
        project_id=pid,
        name="수정없는 산출물",
        artifact_type="code",
        status="reviewed",
        revision_count=0,
    )
    a2 = Artifact(
        project_id=pid,
        name="수정된 산출물",
        artifact_type="code",
        status="released",
        revision_count=2,
    )
    db_session.add_all([a1, a2])
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/reports/projects/{project_id}/kpi",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()

    # avg_phase_duration: "requested" → 3600초
    assert len(body["avg_phase_duration"]) == 1
    assert body["avg_phase_duration"][0]["phase"] == "requested"
    assert body["avg_phase_duration"][0]["avg_duration_seconds"] == 3600.0
    assert body["avg_phase_duration"][0]["sample_count"] == 1

    # throughput_per_week: 완료 2개
    total_completed = sum(w["completed_count"] for w in body["throughput_per_week"])
    assert total_completed == 2

    # automation_rate: 2/3 ≈ 66.7%
    assert body["automation_rate"] == 66.7

    # review_acceptance_rate: 1/2 = 50.0%
    assert body["review_acceptance_rate"] == 50.0


@pytest.mark.asyncio
async def test_get_project_kpi_no_auth(
    client: AsyncClient, project_id: str
) -> None:
    """인증 없이 KPI 조회 → 401/403."""
    resp = await client.get(f"/api/v1/reports/projects/{project_id}/kpi")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_project_kpi_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 프로젝트 KPI → 404."""
    resp = await client.get(
        "/api/v1/reports/projects/00000000-0000-0000-0000-000000000000/kpi",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# === 플랫폼 요약 테스트 ===


@pytest.fixture
async def superadmin_headers(
    client: AsyncClient, db_session: AsyncSession
) -> dict[str, str]:
    """superadmin 사용자 생성 후 인증 헤더 반환."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@example.com",
            "password": "adminpassword123",
            "display_name": "슈퍼어드민",
        },
    )
    # DB에서 역할 변경
    result = await db_session.execute(
        select(User).where(User.email == "admin@example.com")
    )
    admin = result.scalar_one()
    admin.system_role = "superadmin"  # type: ignore[assignment]
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "adminpassword123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_get_platform_summary_superadmin(
    client: AsyncClient, superadmin_headers: dict[str, str]
) -> None:
    """superadmin으로 플랫폼 요약 조회 → 성공."""
    resp = await client.get(
        "/api/v1/reports/platform/summary",
        headers=superadmin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "total_projects" in body
    assert "total_sessions" in body
    assert "total_subtasks" in body
    assert body["automation_rate"] >= 0.0
    assert body["review_acceptance_rate"] >= 0.0
    assert "generated_at" in body


@pytest.mark.asyncio
async def test_get_platform_summary_non_superadmin(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """일반 사용자가 플랫폼 요약 조회 → 403."""
    resp = await client.get(
        "/api/v1/reports/platform/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_platform_summary_no_auth(client: AsyncClient) -> None:
    """인증 없이 플랫폼 요약 → 401/403."""
    resp = await client.get("/api/v1/reports/platform/summary")
    assert resp.status_code in (401, 403)
