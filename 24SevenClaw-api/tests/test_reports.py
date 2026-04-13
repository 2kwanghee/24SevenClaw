"""프로젝트 리포트 API 테스트."""

import pytest
from httpx import AsyncClient


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
