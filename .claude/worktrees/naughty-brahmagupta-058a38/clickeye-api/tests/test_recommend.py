"""추천 엔진 API 테스트."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_recommend_saas(client: AsyncClient) -> None:
    """SaaS 솔루션 유형 추천."""
    resp = await client.post("/api/v1/recommend", json={"solution_type": "saas"})
    assert resp.status_code == 200

    data = resp.json()
    assert data["solution_type"] == "saas"
    assert len(data["agents"]) > 0
    assert len(data["skills"]) > 0
    assert len(data["pipelines"]) > 0

    agent_ids = [a["id"] for a in data["agents"]]
    assert "claude-code" in agent_ids
    assert "cursor" in agent_ids

    # reasoning 필드 확인
    for agent in data["agents"]:
        assert "reasoning" in agent
        assert isinstance(agent["reasoning"], str)
    for skill in data["skills"]:
        assert "reasoning" in skill
    for pipeline in data["pipelines"]:
        assert "reasoning" in pipeline

    # summary 필드 확인
    assert "summary" in data
    assert "SaaS" in data["summary"]


@pytest.mark.asyncio
async def test_recommend_rest_api(client: AsyncClient) -> None:
    """REST API 솔루션 유형 추천."""
    resp = await client.post("/api/v1/recommend", json={"solution_type": "rest-api"})
    assert resp.status_code == 200

    data = resp.json()
    assert data["solution_type"] == "rest-api"

    agent_ids = [a["id"] for a in data["agents"]]
    assert "claude-code" in agent_ids

    skill_ids = [s["id"] for s in data["skills"]]
    assert "tdd-smart-coding" in skill_ids


@pytest.mark.asyncio
async def test_recommend_unknown_type_returns_default(client: AsyncClient) -> None:
    """미등록 솔루션 유형은 기본 추천을 반환한다."""
    resp = await client.post(
        "/api/v1/recommend", json={"solution_type": "unknown-type"}
    )
    assert resp.status_code == 200

    data = resp.json()
    assert data["solution_type"] == "unknown-type"
    assert len(data["agents"]) > 0
    assert len(data["skills"]) > 0
    assert len(data["pipelines"]) > 0


@pytest.mark.asyncio
async def test_recommend_case_insensitive(client: AsyncClient) -> None:
    """솔루션 유형은 대소문자를 구분하지 않는다."""
    resp = await client.post("/api/v1/recommend", json={"solution_type": "SaaS"})
    assert resp.status_code == 200
    assert resp.json()["solution_type"] == "saas"


@pytest.mark.asyncio
async def test_recommend_empty_type_rejected(client: AsyncClient) -> None:
    """빈 솔루션 유형은 422 에러를 반환한다."""
    resp = await client.post("/api/v1/recommend", json={"solution_type": ""})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_recommend_no_auth_required(client: AsyncClient) -> None:
    """추천 API는 인증 없이 접근 가능하다."""
    resp = await client.post("/api/v1/recommend", json={"solution_type": "backend"})
    assert resp.status_code == 200
