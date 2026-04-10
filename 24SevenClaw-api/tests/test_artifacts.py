"""산출물 상태 머신 API 테스트."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    """테스트용 프로젝트 생성 후 ID 반환."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def artifact_id(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> str:
    """테스트용 산출물 생성 후 ID 반환."""
    resp = await client.post(
        f"/api/v1/artifacts/projects/{project_id}/artifacts",
        json={
            "name": "테스트 산출물",
            "artifact_type": "code",
            "created_by_ai": "claude-opus",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# === 생성 테스트 ===


@pytest.mark.asyncio
async def test_create_artifact(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """산출물 생성 → 초기 상태 draft."""
    resp = await client.post(
        f"/api/v1/artifacts/projects/{project_id}/artifacts",
        json={
            "name": "새 산출물",
            "artifact_type": "document",
            "description": "설명",
            "created_by_ai": "claude-sonnet",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "새 산출물"
    assert body["status"] == "draft"
    assert body["artifact_type"] == "document"
    assert body["created_by_ai"] == "claude-sonnet"
    assert body["revision_count"] == 0


@pytest.mark.asyncio
async def test_create_artifact_no_auth(client: AsyncClient, project_id: str) -> None:
    """인증 없이 산출물 생성 → 401/403."""
    resp = await client.post(
        f"/api/v1/artifacts/projects/{project_id}/artifacts",
        json={"name": "산출물", "artifact_type": "code"},
    )
    assert resp.status_code in (401, 403)


# === 조회 테스트 ===


@pytest.mark.asyncio
async def test_list_artifacts(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """프로젝트의 산출물 목록 조회."""
    # 2개 생성
    for i in range(2):
        await client.post(
            f"/api/v1/artifacts/projects/{project_id}/artifacts",
            json={"name": f"산출물 {i}", "artifact_type": "code"},
            headers=auth_headers,
        )

    resp = await client.get(
        f"/api/v1/artifacts/projects/{project_id}/artifacts",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_get_artifact(
    client: AsyncClient, auth_headers: dict[str, str], artifact_id: str
) -> None:
    """산출물 상세 조회."""
    resp = await client.get(
        f"/api/v1/artifacts/{artifact_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == artifact_id


@pytest.mark.asyncio
async def test_get_artifact_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 산출물 조회 → 404."""
    resp = await client.get(
        "/api/v1/artifacts/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# === 상태 전이 테스트 ===


@pytest.mark.asyncio
async def test_transition_draft_to_reviewed(
    client: AsyncClient, auth_headers: dict[str, str], artifact_id: str
) -> None:
    """draft → reviewed 전이 성공."""
    resp = await client.put(
        f"/api/v1/artifacts/{artifact_id}/transition",
        json={
            "target_status": "reviewed",
            "actor_type": "agent",
            "message": "리뷰 완료",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["artifact"]["status"] == "reviewed"
    assert body["event"]["old_status"] == "draft"
    assert body["event"]["new_status"] == "reviewed"
    assert body["event"]["event_type"] == "status_transition"


@pytest.mark.asyncio
async def test_transition_invalid(
    client: AsyncClient, auth_headers: dict[str, str], artifact_id: str
) -> None:
    """draft → approved 전이 불가 → 422."""
    resp = await client.put(
        f"/api/v1/artifacts/{artifact_id}/transition",
        json={"target_status": "approved", "actor_type": "user"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_full_lifecycle(
    client: AsyncClient, auth_headers: dict[str, str], artifact_id: str
) -> None:
    """draft → reviewed → approved → in_development → validated → released 전체 흐름."""
    transitions = [
        ("reviewed", "agent"),
        ("approved", "user"),
        ("in_development", "system"),
        ("validated", "agent"),
        ("released", "user"),
    ]
    for target, actor in transitions:
        resp = await client.put(
            f"/api/v1/artifacts/{artifact_id}/transition",
            json={"target_status": target, "actor_type": actor},
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"{target} 전이 실패: {resp.json()}"
        assert resp.json()["artifact"]["status"] == target


@pytest.mark.asyncio
async def test_revision_cycle(
    client: AsyncClient, auth_headers: dict[str, str], artifact_id: str
) -> None:
    """draft → reviewed → revised → reviewed → approved (리비전 사이클)."""
    for target in ["reviewed", "revised", "reviewed", "approved"]:
        resp = await client.put(
            f"/api/v1/artifacts/{artifact_id}/transition",
            json={"target_status": target, "actor_type": "user"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    # revision_count가 1 증가했는지 확인
    resp = await client.get(
        f"/api/v1/artifacts/{artifact_id}",
        headers=auth_headers,
    )
    assert resp.json()["revision_count"] == 1


@pytest.mark.asyncio
async def test_released_no_transition(
    client: AsyncClient, auth_headers: dict[str, str], artifact_id: str
) -> None:
    """released 상태에서 더 이상 전이 불가."""
    for target in ["reviewed", "approved", "in_development", "validated", "released"]:
        resp = await client.put(
            f"/api/v1/artifacts/{artifact_id}/transition",
            json={"target_status": target, "actor_type": "user"},
            headers=auth_headers,
        )
    # released까지 도달 후 다시 전이 시도
    resp = await client.put(
        f"/api/v1/artifacts/{artifact_id}/transition",
        json={"target_status": "draft", "actor_type": "user"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === 이력 조회 테스트 ===


@pytest.mark.asyncio
async def test_get_history(
    client: AsyncClient, auth_headers: dict[str, str], artifact_id: str
) -> None:
    """전이 후 이력 조회."""
    # 한 번 전이
    await client.put(
        f"/api/v1/artifacts/{artifact_id}/transition",
        json={"target_status": "reviewed", "actor_type": "agent", "message": "1차 리뷰"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/artifacts/{artifact_id}/history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) == 1
    assert events[0]["old_status"] == "draft"
    assert events[0]["new_status"] == "reviewed"
    assert events[0]["message"] == "1차 리뷰"
