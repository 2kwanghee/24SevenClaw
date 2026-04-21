"""ZIP 생성 API 테스트."""

import zipfile
from io import BytesIO

import pytest
from httpx import AsyncClient

from app.schemas.generate import GenerateRequest
from app.services.generate_service import generate_zip

# ── 서비스 단위 테스트 ──


def test_generate_zip_basic() -> None:
    """기본 설정으로 ZIP 생성 확인."""
    request = GenerateRequest(
        solution={
            "projectName": "test-app",
            "solutionType": "fullstack",
            "stackPreset": "fastapi-nextjs",
        },
        agents=["backend"],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    buffer = generate_zip(request, "test-app")

    assert isinstance(buffer, BytesIO)
    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert len(names) > 0
        assert "CLAUDE.md" in names
        assert ".claude/settings.json" in names


def test_generate_zip_includes_onboarding_docs() -> None:
    """ZIP에 docs/api-keys 가이드 4종 포함 확인."""
    request = GenerateRequest(
        solution={"projectName": "onboarding-test", "stackPreset": "fastapi-nextjs"},
        agents=["backend"],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    buffer = generate_zip(request, "onboarding-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert "docs/api-keys/anthropic-api-key-guide.md" in names
        assert "docs/api-keys/linear-api-key-guide.md" in names
        assert "docs/api-keys/claude-code-subscription-guide.md" in names
        assert "docs/api-keys/gemini-api-key-guide.md" in names


def test_generate_zip_includes_start_command_claude() -> None:
    """claude-code 플랫폼 ZIP에 /24SeventStart 커맨드 포함 확인."""
    request = GenerateRequest(
        solution={"projectName": "cmd-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    buffer = generate_zip(request, "cmd-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".claude/commands/24SeventStart.md" in names
        content = zf.read(".claude/commands/24SeventStart.md").decode()
        assert "24SevenClaw" in content
        assert "ANTHROPIC_API_KEY" in content


def test_generate_zip_start_command_gemini() -> None:
    """gemini-cli 플랫폼 ZIP에 Gemini용 커맨드 경로 확인."""
    request = GenerateRequest(
        solution={"projectName": "gemini-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=[],
        platform={"platformId": "gemini-cli"},
    )

    buffer = generate_zip(request, "gemini-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".gemini/commands/24SeventStart.md" in names


def test_generate_zip_linear_skill_includes_team_id() -> None:
    """linear 스킬 선택 시 .env.example에 LINEAR_TEAM_ID 포함 확인."""
    request = GenerateRequest(
        solution={"projectName": "linear-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["linear"],
        platform={"platformId": "claude-code"},
    )

    buffer = generate_zip(request, "linear-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".env.example" in names
        example = zf.read(".env.example").decode()
        assert "LINEAR_API_KEY=" in example
        assert "LINEAR_TEAM_ID=" in example


def test_generate_zip_with_env_vars() -> None:
    """envVars 전달 시 .env + .env.example 포함."""
    request = GenerateRequest(
        solution={"projectName": "my-app", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=[],
        platform={"platformId": "claude-code"},
        env_vars={
            "OPENAI_API_KEY": "sk-test-12345",
            "ANTHROPIC_API_KEY": "sk-ant-test-67890",
        },
    )

    buffer = generate_zip(request, "my-app")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()

        # .env 존재 및 값 포함
        assert ".env" in names
        env_content = zf.read(".env").decode()
        assert "OPENAI_API_KEY=sk-test-12345" in env_content
        assert "ANTHROPIC_API_KEY=sk-ant-test-67890" in env_content

        # .env.example 존재 및 값 미포함
        assert ".env.example" in names
        example_content = zf.read(".env.example").decode()
        assert "OPENAI_API_KEY=" in example_content
        assert "sk-test-12345" not in example_content
        assert "ANTHROPIC_API_KEY=" in example_content
        assert "sk-ant-test-67890" not in example_content


def test_generate_zip_without_env_vars() -> None:
    """envVars 없으면 .env 파일 미포함."""
    request = GenerateRequest(
        solution={"projectName": "no-env", "stackPreset": "custom"},
        agents=[],
        skills=[],
        platform={"platformId": "claude-code"},
    )

    buffer = generate_zip(request, "no-env")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".env" not in names
        assert ".env.example" not in names


def test_generate_zip_valid_zipfile() -> None:
    """생성된 ZIP 파일이 유효한 ZIP 포맷인지 확인."""
    request = GenerateRequest(
        solution={"projectName": "valid-zip", "stackPreset": "fastapi-nextjs"},
        agents=["backend", "frontend"],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
        env_vars={"API_KEY": "test-value"},
    )

    buffer = generate_zip(request, "valid-zip")

    assert zipfile.is_zipfile(buffer)
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as zf:
        # 손상된 파일 없음
        assert zf.testzip() is None


# ── API 엔드포인트 테스트 ──


@pytest.mark.asyncio
async def test_generate_endpoint(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """POST /projects/{id}/generate 정상 동작."""
    # 프로젝트 생성
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "ZIP 테스트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # ZIP 생성 요청
    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {
                "projectName": "zip-test",
                "solutionType": "fullstack",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": ["backend"],
            "skills": ["tdd"],
            "platform": {"platformId": "claude-code"},
            "env_vars": {"OPENAI_API_KEY": "sk-test"},
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert "zip-test.zip" in resp.headers["content-disposition"]

    # ZIP 내용 검증
    buffer = BytesIO(resp.content)
    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert "CLAUDE.md" in names
        assert ".env" in names
        assert ".env.example" in names


@pytest.mark.asyncio
async def test_generate_endpoint_unauthorized(client: AsyncClient) -> None:
    """인증 없이 ZIP 생성 요청 시 401."""
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/generate",
        json={"solution": {}, "agents": [], "skills": [], "platform": {}},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_generate_endpoint_project_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 프로젝트에 ZIP 생성 요청 시 404."""
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/generate",
        json={"solution": {}, "agents": [], "skills": [], "platform": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 404
