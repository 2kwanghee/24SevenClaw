"""마스터 PM AI 오케스트레이터 API 테스트."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    """테스트용 프로젝트 생성 후 ID 반환."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "오케스트레이터 테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def session_id(client: AsyncClient, auth_headers: dict[str, str], project_id: str) -> str:
    """테스트용 오케스트레이션 세션 생성 후 ID 반환."""
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={
            "title": "백엔드 API 보안 강화",
            "description": "인증 API의 보안 취약점 분석 및 개선",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# === 세션 생성 테스트 ===


@pytest.mark.asyncio
async def test_create_session(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """세션 생성 → 초기 단계 requested, 리스크 자동 탐지."""
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={
            "title": "프로덕션 배포 마이그레이션",
            "description": "데이터베이스 마이그레이션 및 보안 검토",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["phase"] == "requested"
    assert body["title"] == "프로덕션 배포 마이그레이션"
    # 리스크 자동 탐지 확인
    assert "production_risk" in body["risk_flags"]
    assert "migration_risk" in body["risk_flags"]
    assert "security_risk" in body["risk_flags"]


@pytest.mark.asyncio
async def test_create_session_no_auth(client: AsyncClient, project_id: str) -> None:
    """인증 없이 세션 생성 → 401/403."""
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "테스트"},
    )
    assert resp.status_code in (401, 403)


# === 세션 조회 테스트 ===


@pytest.mark.asyncio
async def test_list_sessions(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """세션 목록 조회."""
    for i in range(2):
        await client.post(
            f"/api/v1/orchestrator/projects/{project_id}/sessions",
            json={"title": f"세션 {i}"},
            headers=auth_headers,
        )

    resp = await client.get(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_get_session(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """세션 상세 조회."""
    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == session_id


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """존재하지 않는 세션 → 404."""
    resp = await client.get(
        "/api/v1/orchestrator/sessions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# === 작업 분해 테스트 ===


@pytest.mark.asyncio
async def test_decompose(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """작업 분해 → 서브태스크 자동 생성, 단계 decomposed 전이."""
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={"hints": ["API 엔드포인트 개선", "테스트 추가"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["phase"] == "decomposed"
    assert len(body["subtasks"]) > 0
    # 서브태스크에 역할이 배정되었는지 확인
    valid_roles = ("architect", "frontend", "backend", "qa", "security", "devops", "reviewer")
    roles = [st["assigned_role"] for st in body["subtasks"]]
    assert all(r in valid_roles for r in roles)


@pytest.mark.asyncio
async def test_decompose_wrong_phase(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """requested가 아닌 단계에서 분해 시도 → 422."""
    # 먼저 분해하여 decomposed로 전이
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={},
        headers=auth_headers,
    )
    # 다시 분해 시도
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === 팀 배정 테스트 ===


@pytest.mark.asyncio
async def test_assign(client: AsyncClient, auth_headers: dict[str, str], session_id: str) -> None:
    """분해 후 팀 배정 → 단계 assigned 전이."""
    # 1. 분해
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={},
        headers=auth_headers,
    )
    # 2. 배정
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/assign",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["phase"] == "assigned"
    assert len(body["subtasks"]) > 0


# === 단계 전이 테스트 ===


@pytest.mark.asyncio
async def test_transition_flow(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """decompose → assign → 수동 전이로 전체 흐름 테스트."""
    # 분해 & 배정
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/assign",
        json={},
        headers=auth_headers,
    )

    # assigned → drafting → ... → completed (전체 단계 순회)
    phases = [
        "drafting",
        "reviewing",
        "integrating",
        "validating",
        "approved",
        "transitioning",
        "completed",
    ]
    for target in phases:
        resp = await client.put(
            f"/api/v1/orchestrator/sessions/{session_id}/transition",
            json={"target_phase": target},
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"{target} 전이 실패: {resp.json()}"
        assert resp.json()["phase"] == target


@pytest.mark.asyncio
async def test_transition_invalid(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """requested → completed 직접 전이 불가 → 422."""
    resp = await client.put(
        f"/api/v1/orchestrator/sessions/{session_id}/transition",
        json={"target_phase": "completed"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_review_rejection_cycle(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """리뷰 실패 시 drafting으로 되돌아가는 사이클 테스트."""
    # 분해 & 배정
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/assign",
        json={},
        headers=auth_headers,
    )

    # assigned → drafting → reviewing → drafting (리뷰 거절) → reviewing
    for target in ["drafting", "reviewing", "drafting", "reviewing"]:
        resp = await client.put(
            f"/api/v1/orchestrator/sessions/{session_id}/transition",
            json={"target_phase": target, "message": f"{target} 전이"},
            headers=auth_headers,
        )
        assert resp.status_code == 200


# === 이력 조회 테스트 ===


@pytest.mark.asyncio
async def test_phase_history(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """단계 변경 이력 조회."""
    # 초기 이벤트(requested) + 분해(decomposed) = 2개
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}/history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 2
    assert events[0]["new_phase"] == "requested"
    assert events[1]["old_phase"] == "requested"
    assert events[1]["new_phase"] == "decomposed"


# === 리스크 탐지 테스트 ===


@pytest.mark.asyncio
async def test_detect_risks(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """리스크 탐지 엔드포인트."""
    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}/risks",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    risks = resp.json()
    # "보안" 키워드가 포함된 세션이므로 security_risk 탐지
    assert "security_risk" in risks


# === 서브태스크 관리 테스트 ===


@pytest.mark.asyncio
async def test_create_subtask_manually(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """서브태스크 수동 생성."""
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/subtasks",
        json={
            "title": "추가 보안 검토",
            "assigned_role": "security",
            "order_index": 0,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "추가 보안 검토"
    assert body["assigned_role"] == "security"
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_update_subtask(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """서브태스크 상태 업데이트."""
    # 생성
    create_resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/subtasks",
        json={"title": "테스트 작업", "assigned_role": "qa", "order_index": 0},
        headers=auth_headers,
    )
    subtask_id = create_resp.json()["id"]

    # 업데이트
    resp = await client.patch(
        f"/api/v1/orchestrator/subtasks/{subtask_id}",
        json={"status": "completed", "result_summary": "테스트 통과"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["result_summary"] == "테스트 통과"


@pytest.mark.asyncio
async def test_list_subtasks(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """서브태스크 목록 조회."""
    # 2개 생성
    for i in range(2):
        await client.post(
            f"/api/v1/orchestrator/sessions/{session_id}/subtasks",
            json={"title": f"서브태스크 {i}", "assigned_role": "backend", "order_index": i},
            headers=auth_headers,
        )

    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}/subtasks",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


# === 세션 요약 테스트 ===


@pytest.mark.asyncio
async def test_session_summary(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """세션 요약 보고서 조회."""
    # 분해하여 서브태스크 생성
    await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/decompose",
        json={},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session"]["id"] == session_id
    assert len(body["subtasks"]) > 0
    assert len(body["phase_history"]) >= 2  # requested + decomposed
