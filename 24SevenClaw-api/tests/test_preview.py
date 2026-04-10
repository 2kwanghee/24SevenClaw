"""프리뷰 API 테스트."""

import pytest
from httpx import AsyncClient

from app.engine.generator import generate_all
from app.schemas.preview import PreviewRequest
from app.services.preview_service import generate_preview

# ── 생성 엔진 단위 테스트 ──


def test_generate_all_basic() -> None:
    """기본 설정으로 파일 생성 확인."""
    files = generate_all(
        project_name="test-project",
        project_type="fullstack",
        stack_id="fastapi-nextjs",
        agent_ids=["backend", "frontend"],
        workflow_ids=["tdd"],
        platform_id="claude-code",
    )

    assert isinstance(files, dict)
    assert len(files) > 0

    # 필수 파일 존재 확인
    assert "CLAUDE.md" in files
    assert ".claude/settings.json" in files
    # harness는 required=True이므로 항상 포함
    assert ".claude/agents/harness-guide.md" in files
    # 선택한 에이전트
    assert ".claude/agents/api-agent.md" in files
    assert ".claude/agents/web-agent.md" in files
    # 선택한 스킬
    assert ".claude/skills/tdd-smart-coding.md" in files


def test_generate_all_with_ralph_loop() -> None:
    """ralph-loop 워크플로우 선택 시 fix_plan.md 생성."""
    files = generate_all(
        project_name="my-project",
        project_type="fullstack",
        stack_id="fastapi-nextjs",
        agent_ids=[],
        workflow_ids=["ralph-loop"],
    )

    assert ".ralph/fix_plan.md" in files
    assert "Fix Plan" in files[".ralph/fix_plan.md"]


def test_generate_all_with_harness_gate() -> None:
    """harness-gate 선택 시 Hook 스크립트 + run-tests.sh 생성."""
    files = generate_all(
        project_name="my-project",
        project_type="fullstack",
        stack_id="fastapi-nextjs",
        agent_ids=[],
        workflow_ids=["harness-gate"],
    )

    assert "scripts/harness-gate.sh" in files
    assert "scripts/run-tests.sh" in files
    assert ".claude/skills/harness-gate.md" in files


def test_generate_all_custom_stack() -> None:
    """custom 스택에서는 run-tests.sh 미생성."""
    files = generate_all(
        project_name="my-project",
        project_type="custom",
        stack_id="custom",
        agent_ids=[],
        workflow_ids=["tdd"],
    )

    assert "scripts/run-tests.sh" not in files
    assert ".claude/skills/tdd-smart-coding.md" in files


def test_generate_all_cursor_platform() -> None:
    """cursor 플랫폼에서 .cursor/ 디렉토리 사용."""
    files = generate_all(
        project_name="cursor-project",
        project_type="fullstack",
        stack_id="fastapi-nextjs",
        agent_ids=["backend"],
        workflow_ids=[],
        platform_id="cursor",
    )

    assert ".cursorrules" in files
    assert ".cursor/settings.json" in files
    assert ".cursor/rules/api-agent.md" in files
    assert ".cursor/rules/harness-guide.md" in files


def test_generate_all_template_content() -> None:
    """생성된 파일 내용에 프로젝트명이 반영되는지 확인."""
    files = generate_all(
        project_name="MyApp",
        project_type="webapp",
        stack_id="django-react",
        agent_ids=["backend"],
        workflow_ids=[],
    )

    claude_md = files["CLAUDE.md"]
    assert "MyApp" in claude_md
    assert "webapp" in claude_md
    assert "Django + DRF" in claude_md

    api_agent = files[".claude/agents/api-agent.md"]
    assert "MyApp" in api_agent
    assert "Django + DRF" in api_agent


def test_generate_all_empty_workflows() -> None:
    """워크플로우 없이도 기본 파일 생성."""
    files = generate_all(
        project_name="test",
        project_type="fullstack",
        stack_id="fastapi-nextjs",
        agent_ids=[],
        workflow_ids=[],
    )

    # 기본 파일만 존재
    assert "CLAUDE.md" in files
    assert ".claude/settings.json" in files
    assert ".claude/agents/harness-guide.md" in files
    # 스킬 파일 없음
    skill_files = [k for k in files if "/skills/" in k]
    assert len(skill_files) == 0


# ── 프리뷰 서비스 테스트 ──


def test_preview_service_response_structure() -> None:
    """프리뷰 서비스 응답 구조 검증."""
    request = PreviewRequest(
        solution={
            "projectName": "test-app",
            "solutionType": "fullstack",
            "stackPreset": "fastapi-nextjs",
        },
        agents=["backend", "frontend"],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    response = generate_preview(request)

    assert len(response.files) > 0
    assert len(response.file_tree) > 0

    # 파일 트리에 루트 노드 존재 확인
    root_paths = [n.path for n in response.file_tree]
    assert any(".claude" in p for p in root_paths) or any(
        n.children for n in response.file_tree
    )


def test_preview_service_file_tree_structure() -> None:
    """파일 트리가 올바른 계층 구조인지 검증."""
    request = PreviewRequest(
        solution={"projectName": "my-app", "stackPreset": "fastapi-nextjs"},
        agents=["backend"],
        skills=["tdd", "ralph-loop"],
        platform={"platformId": "claude-code"},
    )

    response = generate_preview(request)

    # .claude 디렉토리가 트리에 있는지
    claude_nodes = [n for n in response.file_tree if n.path == ".claude"]
    assert len(claude_nodes) == 1
    claude_node = claude_nodes[0]
    assert claude_node.type == "directory"
    assert len(claude_node.children) > 0


# ── API 엔드포인트 테스트 ──


@pytest.mark.asyncio
async def test_preview_endpoint(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """POST /projects/{id}/preview 정상 동작."""
    # 프로젝트 생성
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]

    # 프리뷰 요청
    resp = await client.post(
        f"/api/v1/projects/{project_id}/preview",
        json={
            "solution": {
                "projectName": "테스트 프로젝트",
                "solutionType": "fullstack",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": ["backend", "frontend"],
            "skills": ["tdd"],
            "platform": {"platformId": "claude-code"},
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "file_tree" in data
    assert "files" in data
    assert len(data["files"]) > 0
    assert "CLAUDE.md" in data["files"]


@pytest.mark.asyncio
async def test_preview_endpoint_unauthorized(client: AsyncClient) -> None:
    """인증 없이 프리뷰 요청 시 401."""
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/preview",
        json={"solution": {}, "agents": [], "skills": [], "platform": {}},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_preview_endpoint_project_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 프로젝트에 프리뷰 요청 시 404."""
    resp = await client.post(
        "/api/v1/projects/00000000-0000-0000-0000-000000000001/preview",
        json={"solution": {}, "agents": [], "skills": [], "platform": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 404
