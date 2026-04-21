"""Draft 엔드포인트 (프리뷰/ZIP 생성) 테스트."""

import pytest
from httpx import AsyncClient

DRAFT_PREVIEW_URL = "/api/v1/projects/draft/preview"
DRAFT_GENERATE_URL = "/api/v1/projects/draft/generate"

VALID_PREVIEW_PAYLOAD = {
    "organization": {"name": "테스트 회사"},
    "solution": {
        "projectName": "test-project",
        "solutionType": "fullstack",
        "stackPreset": "custom",
    },
    "agents": ["backend"],
    "skills": [],
    "pipelines": [],
    "platform": {"platformId": "claude-code"},
}

VALID_GENERATE_PAYLOAD = {
    **VALID_PREVIEW_PAYLOAD,
    "env_vars": {"ANTHROPIC_API_KEY": "sk-test-key"},
}


# --- Draft Preview ---


@pytest.mark.asyncio
async def test_draft_preview_success(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """인증된 사용자의 드래프트 프리뷰 성공."""
    resp = await client.post(
        DRAFT_PREVIEW_URL, json=VALID_PREVIEW_PAYLOAD, headers=auth_headers
    )
    assert resp.status_code == 200

    data = resp.json()
    assert "file_tree" in data
    assert "files" in data
    assert isinstance(data["file_tree"], list)
    assert isinstance(data["files"], dict)


@pytest.mark.asyncio
async def test_draft_preview_unauthenticated(client: AsyncClient) -> None:
    """비인증 사용자 드래프트 프리뷰 거부."""
    resp = await client.post(DRAFT_PREVIEW_URL, json=VALID_PREVIEW_PAYLOAD)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_draft_preview_empty_payload(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """빈 payload로 프리뷰 — 기본값으로 동작."""
    resp = await client.post(DRAFT_PREVIEW_URL, json={}, headers=auth_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert "file_tree" in data
    assert "files" in data


@pytest.mark.asyncio
async def test_draft_preview_invalid_json(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """잘못된 JSON 형식 거부."""
    resp = await client.post(
        DRAFT_PREVIEW_URL,
        content="not-valid-json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 422


# --- Draft Generate (ZIP) ---


@pytest.mark.asyncio
async def test_draft_generate_success(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """인증된 사용자의 드래프트 ZIP 생성 성공."""
    resp = await client.post(
        DRAFT_GENERATE_URL, json=VALID_GENERATE_PAYLOAD, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "content-disposition" in resp.headers
    assert "test-project.zip" in resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_draft_generate_unauthenticated(client: AsyncClient) -> None:
    """비인증 사용자 ZIP 생성 거부."""
    resp = await client.post(DRAFT_GENERATE_URL, json=VALID_GENERATE_PAYLOAD)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_draft_generate_minimal_payload(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """최소 payload로 ZIP 생성."""
    resp = await client.post(
        DRAFT_GENERATE_URL,
        json={"env_vars": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"


@pytest.mark.asyncio
async def test_draft_generate_invalid_json(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """잘못된 JSON 형식 거부."""
    resp = await client.post(
        DRAFT_GENERATE_URL,
        content="not-valid-json",
        headers={**auth_headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 422
