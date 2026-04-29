import pytest
from httpx import AsyncClient

SAMPLE_WIZARD_DATA = {
    "wizard_data": {
        "organization": {"name": "테스트 조직", "size": "small"},
        "solution": {"type": "chatbot", "description": "고객 상담 봇"},
        "agents": [{"name": "claude", "version": "3.5"}],
        "skills": [{"name": "code-review", "enabled": True}],
        "pipelines": [{"name": "deploy", "steps": ["build", "test", "deploy"]}],
        "platform": {"target": "claude-code", "os": "linux"},
    }
}


@pytest.mark.asyncio
async def test_save_wizard_config(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # 프로젝트 생성
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "위저드 테스트"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    # 위저드 설정 저장
    resp = await client.post(
        f"/api/v1/projects/{project_id}/config",
        json=SAMPLE_WIZARD_DATA,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_id"] == project_id
    assert body["wizard_data"]["organization"]["name"] == "테스트 조직"
    assert len(body["wizard_data"]["agents"]) == 1


@pytest.mark.asyncio
async def test_get_wizard_config(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # 프로젝트 생성 + 위저드 설정 저장
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "조회 테스트"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/config",
        json=SAMPLE_WIZARD_DATA,
        headers=auth_headers,
    )

    # 위저드 설정 조회
    resp = await client.get(
        f"/api/v1/projects/{project_id}/config",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["wizard_data"]["solution"]["type"] == "chatbot"
    assert body["wizard_data"]["platform"]["target"] == "claude-code"


@pytest.mark.asyncio
async def test_get_wizard_config_empty(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # 프로젝트 생성 (위저드 설정 없음)
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "빈 설정 테스트"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}/config",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["wizard_data"] is None


@pytest.mark.asyncio
async def test_save_wizard_config_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/config",
        json=SAMPLE_WIZARD_DATA,
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_save_wizard_config_project_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/config",
        json=SAMPLE_WIZARD_DATA,
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_overwrite_wizard_config(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # 프로젝트 생성 + 첫 번째 저장
    create_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "덮어쓰기 테스트"},
        headers=auth_headers,
    )
    project_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/config",
        json=SAMPLE_WIZARD_DATA,
        headers=auth_headers,
    )

    # 두 번째 저장 (덮어쓰기)
    updated_data = {
        "wizard_data": {
            "organization": {"name": "수정된 조직"},
            "solution": {},
            "agents": [],
            "skills": [],
            "pipelines": [],
            "platform": {"target": "gemini-cli"},
        }
    }
    resp = await client.post(
        f"/api/v1/projects/{project_id}/config",
        json=updated_data,
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["wizard_data"]["organization"]["name"] == "수정된 조직"
    assert body["wizard_data"]["platform"]["target"] == "gemini-cli"
