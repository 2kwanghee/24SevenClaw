"""산출물 상태머신 자동 전이 트리거 테스트 (24S-74)."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    """테스트용 프로젝트 생성 후 ID 반환."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "자동 전이 테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def session_at_drafting(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> str:
    """오케스트레이션 세션을 drafting 단계까지 전이한 뒤 ID 반환."""
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "자동 전이 테스트", "description": "API 구현 테스트"},
        headers=auth_headers,
    )
    sid = resp.json()["id"]

    await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/decompose",
        json={},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/assign",
        json={},
        headers=auth_headers,
    )
    await client.put(
        f"/api/v1/orchestrator/sessions/{sid}/transition",
        json={"target_phase": "drafting"},
        headers=auth_headers,
    )
    return sid


# === bulk_transition 테스트 ===


@pytest.mark.asyncio
async def test_bulk_transition_via_approved_phase(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
    session_at_drafting: str,
) -> None:
    """approved 전이 시 연결된 Artifact가 자동으로 approved 전이된다."""
    sid = session_at_drafting

    # 1. 산출물 2개 생성 → draft 상태
    artifact_ids: list[str] = []
    for i in range(2):
        resp = await client.post(
            f"/api/v1/artifacts/projects/{project_id}/artifacts",
            json={"name": f"산출물 {i}", "artifact_type": "code"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        art_id = resp.json()["id"]
        artifact_ids.append(art_id)

        # draft → reviewed 전이 (approved 전이의 전제 조건)
        resp = await client.put(
            f"/api/v1/artifacts/{art_id}/transition",
            json={"target_status": "reviewed", "actor_type": "agent"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    # 2. 서브태스크에 산출물 연결
    subtask_ids: list[str] = []
    for i, art_id in enumerate(artifact_ids):
        resp = await client.post(
            f"/api/v1/orchestrator/sessions/{sid}/subtasks",
            json={
                "title": f"작업 {i}",
                "assigned_role": "backend",
                "order_index": i + 10,
                "artifact_id": art_id,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        subtask_ids.append(resp.json()["id"])

    # 3. 세션을 approved까지 전이
    for phase in ["reviewing", "integrating", "validating", "approved"]:
        resp = await client.put(
            f"/api/v1/orchestrator/sessions/{sid}/transition",
            json={"target_phase": phase},
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"{phase} 전이 실패: {resp.json()}"

    # 4. 산출물 상태 확인 — reviewed → approved 자동 전이
    for art_id in artifact_ids:
        resp = await client.get(
            f"/api/v1/artifacts/{art_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved", (
            f"산출물 {art_id}이 approved가 아닙니다: {resp.json()['status']}"
        )

    # 5. 산출물 이력에 자동 전이 이벤트 기록 확인
    resp = await client.get(
        f"/api/v1/artifacts/{artifact_ids[0]}/history",
        headers=auth_headers,
    )
    events = resp.json()
    auto_event = [e for e in events if e["new_status"] == "approved"]
    assert len(auto_event) == 1
    assert auto_event[0]["actor_type"] == "system"
    assert "자동 갱신" in auto_event[0]["message"]


@pytest.mark.asyncio
async def test_approved_skips_non_reviewed_artifacts(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
    session_at_drafting: str,
) -> None:
    """approved 전이 시 reviewed가 아닌 산출물은 건너뛴다."""
    sid = session_at_drafting

    # draft 상태의 산출물 생성 (reviewed가 아니므로 approved 전이 불가)
    resp = await client.post(
        f"/api/v1/artifacts/projects/{project_id}/artifacts",
        json={"name": "미리뷰 산출물", "artifact_type": "code"},
        headers=auth_headers,
    )
    art_id = resp.json()["id"]

    # 서브태스크에 연결
    await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/subtasks",
        json={
            "title": "작업",
            "assigned_role": "backend",
            "order_index": 10,
            "artifact_id": art_id,
        },
        headers=auth_headers,
    )

    # approved까지 전이
    for phase in ["reviewing", "integrating", "validating", "approved"]:
        resp = await client.put(
            f"/api/v1/orchestrator/sessions/{sid}/transition",
            json={"target_phase": phase},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    # 산출물은 여전히 draft (전이 안 됨)
    resp = await client.get(
        f"/api/v1/artifacts/{art_id}",
        headers=auth_headers,
    )
    assert resp.json()["status"] == "draft"


# === merge 후 자동 전이 테스트 ===


@pytest.mark.asyncio
async def test_merge_auto_transitions_subtask_and_artifact(
    client: AsyncClient,
    auth_headers: dict[str, str],
    project_id: str,
    session_at_drafting: str,
) -> None:
    """merge 후 SubTask → completed, Artifact → reviewed 자동 전이."""
    sid = session_at_drafting

    # 1. 산출물 생성 (draft 상태)
    resp = await client.post(
        f"/api/v1/artifacts/projects/{project_id}/artifacts",
        json={"name": "병합 테스트 산출물", "artifact_type": "code"},
        headers=auth_headers,
    )
    art_id = resp.json()["id"]

    # 2. 서브태스크 생성 + 산출물 연결
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/subtasks",
        json={
            "title": "병합 테스트 작업",
            "assigned_role": "backend",
            "order_index": 10,
            "artifact_id": art_id,
        },
        headers=auth_headers,
    )
    subtask_id = resp.json()["id"]

    # 3. 리뷰 라운드 생성 (서브태스크 연결)
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "def process(): pass",
            "subtask_id": subtask_id,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    round_id = resp.json()["id"]

    # 4. 교차 리뷰 제출
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "def process(): '''처리.'''\n    return True",
            "review_score": 80,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # 5. 병합
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_review"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "merged"

    # 6. 서브태스크 상태 확인 → completed
    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{sid}/subtasks",
        headers=auth_headers,
    )
    subtasks = resp.json()
    matched = [st for st in subtasks if st["id"] == subtask_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "completed"

    # 7. 산출물 상태 확인 → reviewed (draft → reviewed 자동 전이)
    resp = await client.get(
        f"/api/v1/artifacts/{art_id}",
        headers=auth_headers,
    )
    assert resp.json()["status"] == "reviewed"

    # 8. 산출물 이력 확인
    resp = await client.get(
        f"/api/v1/artifacts/{art_id}/history",
        headers=auth_headers,
    )
    events = resp.json()
    auto_events = [e for e in events if e["actor_type"] == "system"]
    assert len(auto_events) >= 1
    assert auto_events[0]["new_status"] == "reviewed"


@pytest.mark.asyncio
async def test_merge_without_subtask_no_error(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_at_drafting: str,
) -> None:
    """subtask_id 없는 리뷰 라운드 병합 시 에러 없이 정상 동작."""
    sid = session_at_drafting

    # subtask_id 없이 리뷰 라운드 생성
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "standalone draft",
        },
        headers=auth_headers,
    )
    round_id = resp.json()["id"]

    # 리뷰 제출 + 병합
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "LGTM",
            "review_score": 90,
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_draft"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "merged"


@pytest.mark.asyncio
async def test_merge_subtask_without_artifact_no_error(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_at_drafting: str,
) -> None:
    """artifact_id 없는 서브태스크 병합 시 SubTask만 completed, 에러 없음."""
    sid = session_at_drafting

    # artifact 없는 서브태스크 생성
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/subtasks",
        json={
            "title": "산출물 없는 작업",
            "assigned_role": "qa",
            "order_index": 10,
        },
        headers=auth_headers,
    )
    subtask_id = resp.json()["id"]

    # 리뷰 라운드 생성 (서브태스크 연결)
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/reviews",
        json={
            "main_ai_role": "qa",
            "draft_content": "test cases",
            "subtask_id": subtask_id,
        },
        headers=auth_headers,
    )
    round_id = resp.json()["id"]

    # 리뷰 + 병합
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "tests look good",
            "review_score": 85,
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_draft"},
        headers=auth_headers,
    )
    assert resp.status_code == 200

    # 서브태스크 상태 확인 → completed
    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{sid}/subtasks",
        headers=auth_headers,
    )
    subtasks = resp.json()
    matched = [st for st in subtasks if st["id"] == subtask_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "completed"
