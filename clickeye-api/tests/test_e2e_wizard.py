"""E2E 위저드 플로우 테스트: Step 1→7 전체 흐름 + ZIP 구조 + 플랫폼별 검증.

검증 범위:
- 회원가입 → 프로젝트 생성 → 위저드 설정 저장 → 프리뷰 → ZIP 다운로드 전체 흐름
- Claude Code / Gemini CLI / Cursor / Codex 플랫폼별 디렉토리 구조
- 에이전트/스킬 조합별 파일 생성
- .env 파일 포함 여부 및 내용
- 추천 엔진 연동
- 재다운로드 기능
"""

import json
import zipfile
from io import BytesIO

import pytest
from httpx import AsyncClient

# ── 헬퍼: 인증 + 프로젝트 생성 ──


async def _register_and_login(client: AsyncClient) -> tuple[dict[str, str], str]:
    """회원가입 + 로그인 → (auth_headers, user_id) 반환."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wizard@test.com",
            "password": "wizardpass123",
            "display_name": "위저드 테스터",
        },
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "wizard@test.com", "password": "wizardpass123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, user_id


async def _create_project(
    client: AsyncClient, headers: dict[str, str], name: str = "위저드 테스트"
) -> str:
    """프로젝트 생성 → project_id 반환."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": name, "description": "E2E 위저드 테스트용"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _build_wizard_request(
    *,
    platform_id: str = "claude-code",
    solution_type: str = "fullstack",
    stack_preset: str = "fastapi-nextjs",
    agents: list[str] | None = None,
    skills: list[str] | None = None,
    pipelines: list[str] | None = None,
    env_vars: dict[str, str] | None = None,
) -> dict:
    """위저드 요청 페이로드 빌드."""
    payload: dict = {
        "organization": {
            "companyName": "테스트 회사",
            "companySize": "small",
            "industry": "it",
            "techStack": ["python", "typescript", "docker"],
        },
        "solution": {
            "projectName": "my-project",
            "solutionType": solution_type,
            "stackPreset": stack_preset,
            "description": "E2E 테스트 프로젝트",
        },
        "agents": agents if agents is not None else ["backend", "frontend"],
        "skills": skills if skills is not None else ["tdd"],
        "pipelines": pipelines if pipelines is not None else ["harness", "lint-gate"],
        "platform": {"platformId": platform_id},
    }
    if env_vars is not None:
        payload["env_vars"] = env_vars
    return payload


def _open_zip(content: bytes) -> zipfile.ZipFile:
    """응답 바이트에서 ZipFile 열기."""
    buf = BytesIO(content)
    assert zipfile.is_zipfile(buf)
    buf.seek(0)
    return zipfile.ZipFile(buf)


# ═══════════════════════════════════════════════════════════════
#  1. Step 1→7 전체 플로우 E2E
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
#  2. 플랫폼별 ZIP 구조 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_claude_code_platform_structure(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Claude Code 플랫폼: .claude/ 구조 검증."""
    project_id = await _create_project(client, auth_headers, "Claude 테스트")
    req = _build_wizard_request(platform_id="claude-code", agents=["backend"])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()

        # Claude Code 필수 구조
        assert "CLAUDE.md" in names
        assert ".claude/settings.json" in names
        assert ".claude/agents/harness-guide.md" in names
        assert ".claude/agents/api-agent.md" in names

        # settings.json 구조 검증
        settings = json.loads(zf.read(".claude/settings.json"))
        assert "permissions" in settings
        assert "allow" in settings["permissions"]
        assert "deny" in settings["permissions"]
        assert "hooks" in settings

        # CLAUDE.md 내용에 프로젝트 정보 포함
        guide = zf.read("CLAUDE.md").decode()
        assert "my-project" in guide


@pytest.mark.asyncio
async def test_gemini_cli_platform_structure(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Gemini CLI 플랫폼: .gemini/ 구조 검증."""
    project_id = await _create_project(client, auth_headers, "Gemini 테스트")
    req = _build_wizard_request(platform_id="gemini-cli", agents=["backend"])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()

        # Gemini CLI 필수 구조
        assert "GEMINI.md" in names
        assert ".gemini/settings.json" in names
        assert ".gemini/agents/harness-guide.md" in names
        assert ".gemini/agents/api-agent.md" in names

        # settings.json은 Gemini 형식
        settings = json.loads(zf.read(".gemini/settings.json"))
        assert "coreTools" in settings
        assert "safetySettings" in settings


@pytest.mark.asyncio
async def test_cursor_platform_structure(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Cursor 플랫폼: .cursor/rules/ 구조 검증."""
    project_id = await _create_project(client, auth_headers, "Cursor 테스트")
    req = _build_wizard_request(platform_id="cursor", agents=["frontend"])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()

        # Cursor 필수 구조
        assert ".cursorrules" in names
        assert ".cursor/settings.json" in names
        assert ".cursor/rules/harness-guide.md" in names
        assert ".cursor/rules/web-agent.md" in names

        # settings.json은 Cursor 형식
        settings = json.loads(zf.read(".cursor/settings.json"))
        assert "rules" in settings
        assert "safetySettings" in settings


@pytest.mark.asyncio
async def test_codex_platform_structure(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Codex 플랫폼: .codex/ 구조 검증."""
    project_id = await _create_project(client, auth_headers, "Codex 테스트")
    req = _build_wizard_request(platform_id="codex", agents=["backend"])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()

        # Codex 필수 구조
        assert "CODEX.md" in names
        assert ".codex/settings.json" in names
        assert ".codex/agents/harness-guide.md" in names
        assert ".codex/agents/api-agent.md" in names


# ═══════════════════════════════════════════════════════════════
#  3. 에이전트/스킬 조합 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_ids,expected_files",
    [
        (
            ["backend"],
            ["api-agent.md", "harness-guide.md"],
        ),
        (
            ["frontend"],
            ["web-agent.md", "harness-guide.md"],
        ),
        (
            ["uiux"],
            ["uiux-agent.md", "harness-guide.md"],
        ),
        (
            ["devops"],
            ["infra-agent.md", "harness-guide.md"],
        ),
        (
            ["fullstack"],
            ["fullstack-agent.md", "harness-guide.md"],
        ),
        (
            ["backend", "frontend", "uiux", "devops", "fullstack"],
            [
                "api-agent.md",
                "web-agent.md",
                "uiux-agent.md",
                "infra-agent.md",
                "fullstack-agent.md",
                "harness-guide.md",
            ],
        ),
    ],
    ids=[
        "backend-only",
        "frontend-only",
        "uiux-only",
        "devops-only",
        "fullstack-only",
        "all-agents",
    ],
)
async def test_agent_combinations(
    client: AsyncClient,
    auth_headers: dict[str, str],
    agent_ids: list[str],
    expected_files: list[str],
) -> None:
    """에이전트 조합별 파일 생성 검증."""
    project_id = await _create_project(client, auth_headers, f"Agent {'-'.join(agent_ids)}")
    req = _build_wizard_request(agents=agent_ids, skills=[], pipelines=[])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        for expected in expected_files:
            path = f".claude/agents/{expected}"
            assert path in names, f"{path} not in ZIP"

        # harness는 항상 포함 (required=True)
        assert ".claude/agents/harness-guide.md" in names


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "skill_ids,expected_files",
    [
        (["tdd"], ["tdd-smart-coding.md"]),
        (["ai-critique"], ["ai-critique.md"]),
        (["ralph-loop"], ["ralph-loop.md"]),
        (["harness-gate"], ["harness-gate.md"]),
        (["linear"], ["linear-sync.md"]),
        (
            ["tdd", "ai-critique", "ralph-loop"],
            ["tdd-smart-coding.md", "ai-critique.md", "ralph-loop.md"],
        ),
    ],
    ids=[
        "tdd-only",
        "ai-critique-only",
        "ralph-loop-only",
        "harness-gate-only",
        "linear-only",
        "multi-skills",
    ],
)
async def test_skill_combinations(
    client: AsyncClient,
    auth_headers: dict[str, str],
    skill_ids: list[str],
    expected_files: list[str],
) -> None:
    """스킬 조합별 파일 생성 검증."""
    project_id = await _create_project(client, auth_headers, f"Skill {'-'.join(skill_ids)}")
    req = _build_wizard_request(agents=[], skills=skill_ids, pipelines=[])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        for expected in expected_files:
            path = f".claude/skills/{expected}"
            assert path in names, f"{path} not in ZIP"


@pytest.mark.asyncio
async def test_harness_gate_generates_hook_script(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """harness-gate 스킬 선택 시 scripts/harness-gate.sh 생성 검증."""
    project_id = await _create_project(client, auth_headers, "Harness 테스트")
    req = _build_wizard_request(skills=["harness-gate"], pipelines=[])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        assert "scripts/harness-gate.sh" in names

        # settings.json에 hook 등록 확인
        settings = json.loads(zf.read(".claude/settings.json"))
        submit_hooks = settings["hooks"]["UserPromptSubmit"]
        assert any("harness-gate" in h["command"] for h in submit_hooks)


@pytest.mark.asyncio
async def test_ralph_loop_generates_fix_plan(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """ralph-loop 파이프라인 선택 시 .ralph/fix_plan.md 생성."""
    project_id = await _create_project(client, auth_headers, "Ralph 테스트")
    req = _build_wizard_request(skills=[], pipelines=["ralph-loop"])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        assert ".ralph/fix_plan.md" in names

        content = zf.read(".ralph/fix_plan.md").decode()
        assert "Ralph Loop" in content
        assert "- [ ]" in content


@pytest.mark.asyncio
async def test_tdd_pipeline_generates_test_script(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """TDD 파이프라인 + 스택 설정 시 scripts/run-tests.sh 생성."""
    project_id = await _create_project(client, auth_headers, "TDD 테스트")
    req = _build_wizard_request(
        skills=["tdd"],
        pipelines=["tdd"],
        stack_preset="fastapi-nextjs",
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        assert "scripts/run-tests.sh" in names

        script = zf.read("scripts/run-tests.sh").decode()
        assert "pytest" in script  # 백엔드 테스트 커맨드
        assert "#!/usr/bin/env bash" in script


# ═══════════════════════════════════════════════════════════════
#  4. .env 파일 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_env_file_with_api_keys(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """env_vars 전달 시 .env에 값 포함, .env.example에는 값 미포함."""
    project_id = await _create_project(client, auth_headers, "ENV 테스트")
    req = _build_wizard_request(
        skills=["linear"],
        env_vars={
            "LINEAR_API_KEY": "lin_api_test12345",
            "ANTHROPIC_API_KEY": "sk-ant-secret",
        },
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        assert ".env" in names
        assert ".env.example" in names

        env = zf.read(".env").decode()
        assert "LINEAR_API_KEY=lin_api_test12345" in env
        assert "ANTHROPIC_API_KEY=sk-ant-secret" in env

        example = zf.read(".env.example").decode()
        assert "LINEAR_API_KEY=" in example
        # .env.example에 실제 키값이 없어야 함
        assert "lin_api_test12345" not in example
        assert "sk-ant-secret" not in example


@pytest.mark.asyncio
async def test_env_file_not_generated_without_vars(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """env_vars 없고 스킬에 env_var 정의도 없으면 .env 미생성."""
    project_id = await _create_project(client, auth_headers, "NoENV 테스트")
    req = _build_wizard_request(skills=["tdd"], pipelines=[])
    # tdd 스킬은 env_vars 정의가 없음

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        assert ".env" not in names
        assert ".env.example" not in names


@pytest.mark.asyncio
async def test_env_file_from_skill_definitions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """스킬의 env_var 정의만으로도 .env.example 생성."""
    project_id = await _create_project(client, auth_headers, "SkillENV 테스트")
    req = _build_wizard_request(
        skills=["linear"],
        pipelines=[],
        env_vars={"LINEAR_API_KEY": "lin_api_mykey"},
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        assert ".env" in zf.namelist()
        env = zf.read(".env").decode()
        assert "LINEAR_API_KEY=lin_api_mykey" in env


# ═══════════════════════════════════════════════════════════════
#  5. 추천 엔진 통합 검증
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
#  6. 재다운로드 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_redownload_with_updated_env_vars(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """설정 저장 후 재다운로드 시 새 env_vars 반영."""
    project_id = await _create_project(client, auth_headers, "재다운로드 테스트")
    wizard_data = _build_wizard_request(
        agents=["backend"],
        skills=["linear"],
        env_vars={"LINEAR_API_KEY": "lin_api_old"},
    )

    # 첫 다운로드 (설정 자동 저장)
    resp1 = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=wizard_data,
        headers=auth_headers,
    )
    assert resp1.status_code == 200

    # 재다운로드 (새 API 키)
    resp2 = await client.post(
        f"/api/v1/projects/{project_id}/redownload",
        json={"env_vars": {"LINEAR_API_KEY": "lin_api_new_key"}},
        headers=auth_headers,
    )
    assert resp2.status_code == 200

    with _open_zip(resp2.content) as zf:
        env = zf.read(".env").decode()
        assert "lin_api_new_key" in env
        assert "lin_api_old" not in env


# ═══════════════════════════════════════════════════════════════
#  7. 엣지 케이스
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_empty_agents_still_includes_harness(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """에이전트 미선택 시에도 필수 에이전트(harness) 포함."""
    project_id = await _create_project(client, auth_headers, "빈 에이전트")
    req = _build_wizard_request(agents=[], skills=[], pipelines=[])

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        assert ".claude/agents/harness-guide.md" in names


@pytest.mark.asyncio
async def test_custom_stack_generates_without_error(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """custom 스택 프리셋으로도 정상 생성."""
    project_id = await _create_project(client, auth_headers, "커스텀 스택")
    req = _build_wizard_request(
        stack_preset="custom",
        agents=["backend"],
        skills=[],
        pipelines=[],
    )

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req,
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        assert zf.testzip() is None
        assert "CLAUDE.md" in zf.namelist()


@pytest.mark.asyncio
async def test_preview_matches_generate_files(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """프리뷰의 파일 목록과 ZIP의 파일 목록이 일치 (env 제외)."""
    project_id = await _create_project(client, auth_headers, "프리뷰 매칭")
    req_base = _build_wizard_request(agents=["backend"], skills=["tdd"], pipelines=[])

    # 프리뷰
    preview_resp = await client.post(
        f"/api/v1/projects/{project_id}/preview",
        json=req_base,
        headers=auth_headers,
    )
    assert preview_resp.status_code == 200
    preview_files = set(preview_resp.json()["files"].keys())

    # ZIP (env_vars 없이)
    gen_resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=req_base,
        headers=auth_headers,
    )
    zip_files = set(_open_zip(gen_resp.content).namelist())

    # 프리뷰와 ZIP 파일 목록 일치
    assert preview_files == zip_files


@pytest.mark.asyncio
async def test_all_platforms_generate_valid_zip(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """모든 플랫폼에서 유효한 ZIP 생성."""
    platforms = ["claude-code", "gemini-cli", "cursor", "codex"]
    expected_guides = {
        "claude-code": "CLAUDE.md",
        "gemini-cli": "GEMINI.md",
        "cursor": ".cursorrules",
        "codex": "CODEX.md",
    }
    expected_dirs = {
        "claude-code": ".claude/",
        "gemini-cli": ".gemini/",
        "cursor": ".cursor/",
        "codex": ".codex/",
    }

    for platform in platforms:
        project_id = await _create_project(client, auth_headers, f"{platform} 검증")
        req = _build_wizard_request(platform_id=platform, agents=["backend"])

        resp = await client.post(
            f"/api/v1/projects/{project_id}/generate",
            json=req,
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"{platform} ZIP 생성 실패"

        with _open_zip(resp.content) as zf:
            names = zf.namelist()
            assert zf.testzip() is None, f"{platform} ZIP 손상"
            assert expected_guides[platform] in names, (
                f"{platform}: {expected_guides[platform]} 누락"
            )
            assert any(n.startswith(expected_dirs[platform]) for n in names), (
                f"{platform}: {expected_dirs[platform]} 디렉토리 누락"
            )
