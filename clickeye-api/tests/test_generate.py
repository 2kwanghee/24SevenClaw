"""ZIP 생성 API 테스트."""

import zipfile
from io import BytesIO

import pytest
from httpx import AsyncClient

from app.schemas.generate import GenerateRequest
from app.services.generate_service import generate_zip
from tests.catalog_test_data import build_test_prefetch, emit_files

# ── 서비스 단위 테스트 ──


@pytest.mark.no_db
async def test_generate_zip_basic() -> None:
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

    buffer = await generate_zip(request, "test-app")

    assert isinstance(buffer, BytesIO)
    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert len(names) > 0
        assert "CLAUDE.md" in names
        assert ".claude/settings.json" in names


@pytest.mark.no_db
async def test_generate_zip_includes_onboarding_docs() -> None:
    """ZIP에 docs/api-keys 가이드 4종 포함 확인."""
    request = GenerateRequest(
        solution={"projectName": "onboarding-test", "stackPreset": "fastapi-nextjs"},
        agents=["backend"],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "onboarding-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert "docs/api-keys/anthropic-api-key-guide.md" in names
        assert "docs/api-keys/linear-api-key-guide.md" in names
        assert "docs/api-keys/claude-code-subscription-guide.md" in names
        assert "docs/api-keys/gemini-api-key-guide.md" in names


@pytest.mark.no_db
async def test_generate_zip_includes_start_command_claude() -> None:
    """claude-code 플랫폼 ZIP에 /ClickEyeStart 커맨드 포함 확인."""
    request = GenerateRequest(
        solution={"projectName": "cmd-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "cmd-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".claude/commands/ClickEyeStart.md" in names
        content = zf.read(".claude/commands/ClickEyeStart.md").decode()
        assert "ClickEye" in content
        # ClickEyeStart 재설계: ANTHROPIC_API_KEY 직접 미포함, start.sh 실행 안내
        assert "start.sh" in content


@pytest.mark.no_db
async def test_generate_zip_start_command_gemini() -> None:
    """gemini-cli 플랫폼 ZIP에 Gemini용 커맨드 경로 확인."""
    request = GenerateRequest(
        solution={"projectName": "gemini-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=[],
        platform={"platformId": "gemini-cli"},
    )

    buffer = await generate_zip(request, "gemini-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".gemini/commands/ClickEyeStart.md" in names


@pytest.mark.no_db
def test_generate_zip_linear_skill_includes_team_id() -> None:
    """linear 스킬 prefetch → .env.example 에 LINEAR_API_KEY/LINEAR_TEAM_ID emit 확인."""
    files = emit_files(skills=["linear"], prefetch=build_test_prefetch(skill_slugs=["linear"]))

    assert ".env.example" in files
    example = files[".env.example"]
    assert isinstance(example, str)
    assert "LINEAR_API_KEY=" in example
    assert "LINEAR_TEAM_ID=" in example


@pytest.mark.no_db
def test_generate_zip_notion_skill_includes_files() -> None:
    """notion 스킬 prefetch → notion-sync.md + .env.example NOTION 키 emit 확인."""
    files = emit_files(skills=["notion"], prefetch=build_test_prefetch(skill_slugs=["notion"]))

    assert ".claude/skills/notion-sync.md" in files
    assert ".env.example" in files
    example = files[".env.example"]
    assert isinstance(example, str)
    assert "NOTION_API_KEY=" in example
    assert "NOTION_DATABASE_ID=" in example
    content = files[".claude/skills/notion-sync.md"]
    assert isinstance(content, str)
    assert "Notion" in content


@pytest.mark.skip(
    reason="selection 격리(linear 시 notion 미포함)는 prefetch_for_generator(DB) 책임. "
    "handcrafted prefetch 로는 near-tautological → DB 통합테스트 필요(follow-up)."
)
async def test_generate_zip_linear_not_broken_after_notion_added() -> None:
    """notion 추가 후 linear 경로 회귀 없음 확인 (selection-isolation, DB 통합테스트 영역)."""
    request = GenerateRequest(
        solution={"projectName": "linear-reg", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["linear"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "linear-reg")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".claude/skills/linear-sync.md" in names
        assert ".claude/skills/notion-sync.md" not in names


# ── 메타프롬프팅 (관측형 사전 정제) emit 테스트 ──
# generate_zip 은 async, catalog_prefetch=None 이면 DB 불필요 → no_db 단위 테스트.


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_generate_zip_linear_skill_includes_metaprompt() -> None:
    """linear 스킬 선택 시 .claude/skills/metaprompt.md(관측형 사전 정제) 포함 확인."""
    request = GenerateRequest(
        solution={"projectName": "metaprompt-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["linear"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "metaprompt-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".claude/skills/metaprompt.md" in names
        content = zf.read(".claude/skills/metaprompt.md").decode()
        # 구조 리팩터(C)에도 안정적인 방법론 마커만 단언 (함수명 등 이동 가능 식별자 제외)
        assert "관측형 사전 정제" in content
        assert "가정 (Assumptions)" in content
        assert "Acceptance Criteria 재확장 금지" in content
        assert "자기 점검" in content


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_generate_zip_run_pipeline_includes_refine_step() -> None:
    """linear 스킬 선택 시 run-pipeline.sh에 관측형 사전 정제 배선 포함 확인."""
    request = GenerateRequest(
        solution={"projectName": "refine-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["linear"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "refine-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert "scripts/run-pipeline.sh" in names
        script = zf.read("scripts/run-pipeline.sh").decode()
        # 안정 마커만 단언: 정제 스킬 참조 / 멱등성 저장 경로 / 구현 콜 prepend·코멘트 헤더
        assert "METAPROMPT_FILE" in script
        assert ".ralph/refined" in script
        assert "정제된 구현 스펙" in script


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_generate_zip_no_linear_skips_metaprompt() -> None:
    """linear 미선택 시 metaprompt.md / run-pipeline.sh 미포함(게이팅) 확인."""
    request = GenerateRequest(
        solution={"projectName": "no-linear-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "no-linear-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".claude/skills/metaprompt.md" not in names
        assert "scripts/run-pipeline.sh" not in names


# ── Linear 게이트 (이슈 없는 직접 개발 차단) emit 테스트 ──


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_generate_zip_linear_skill_includes_gate() -> None:
    """linear 스킬 선택 시 게이트 hook 스크립트 + 토글 스크립트 + settings PreToolUse 등록 확인."""
    import json

    request = GenerateRequest(
        solution={"projectName": "gate-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["linear"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "gate-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        # 게이트 스크립트 파일 emit 확인
        assert "scripts/clickeye-linear-gate.sh" in names
        assert "scripts/clickeye-gate.sh" in names
        assert "docs/CLICKEYE_GATE.md" in names

        # 게이트 hook 본체에 핵심 로직 마커 확인
        gate = zf.read("scripts/clickeye-linear-gate.sh").decode()
        assert "gate-disabled" in gate
        assert "fix_plan.md" in gate

        # 토글 스크립트 on/off 분기 확인
        toggle = zf.read("scripts/clickeye-gate.sh").decode()
        assert "off)" in toggle
        assert "on)" in toggle

        # settings.json 의 PreToolUse 에 게이트 hook 등록 확인
        settings = json.loads(zf.read(".claude/settings.json").decode())
        pre = settings["hooks"]["PreToolUse"]
        gate_entries = [
            e
            for e in pre
            if e.get("matcher") == "Edit|Write|MultiEdit"
            and any("clickeye-linear-gate.sh" in h.get("command", "") for h in e.get("hooks", []))
        ]
        assert gate_entries, "PreToolUse 에 clickeye-linear-gate hook 이 등록되어야 함"


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_generate_zip_no_linear_skips_gate() -> None:
    """linear 미선택 시 게이트 파일/hook 미포함(회귀 방지) 확인."""
    import json

    request = GenerateRequest(
        solution={"projectName": "no-gate-test", "stackPreset": "fastapi-nextjs"},
        agents=[],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "no-gate-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert "scripts/clickeye-linear-gate.sh" not in names
        assert "scripts/clickeye-gate.sh" not in names

        settings = json.loads(zf.read(".claude/settings.json").decode())
        pre = settings["hooks"].get("PreToolUse", [])
        assert not any(
            any("clickeye-linear-gate.sh" in h.get("command", "") for h in e.get("hooks", []))
            for e in pre
        ), "linear 미선택 시 게이트 hook 이 없어야 함"


@pytest.mark.no_db
async def test_generate_zip_with_env_vars() -> None:
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

    buffer = await generate_zip(request, "my-app")

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


@pytest.mark.no_db
async def test_generate_zip_without_env_vars() -> None:
    """envVars 없으면 .env 파일 미포함."""
    request = GenerateRequest(
        solution={"projectName": "no-env", "stackPreset": "custom"},
        agents=[],
        skills=[],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "no-env")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert ".env" not in names
        assert ".env.example" not in names


@pytest.mark.no_db
async def test_generate_zip_valid_zipfile() -> None:
    """생성된 ZIP 파일이 유효한 ZIP 포맷인지 확인."""
    request = GenerateRequest(
        solution={"projectName": "valid-zip", "stackPreset": "fastapi-nextjs"},
        agents=["backend", "frontend"],
        skills=["tdd"],
        platform={"platformId": "claude-code"},
        env_vars={"API_KEY": "test-value"},
    )

    buffer = await generate_zip(request, "valid-zip")

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
