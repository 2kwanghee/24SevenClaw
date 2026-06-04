"""ZIP 엔진 PM 통합 테스트 — 4개 플랫폼별 파일 주입 및 내용 검증."""

import zipfile

import pytest

from app.schemas.generate import GenerateRequest
from app.services.generate_service import generate_zip
from tests.catalog_test_data import build_test_prefetch, emit_files

PM_SLUG = "test-pm"
PM_MARKDOWN = "# Test PM\n\n이것은 테스트 PM 프로필입니다.\n전략 및 실행 역량을 갖춘 PM.\n"


# ── 플랫폼별 PM 파일 경로 검증 ──


@pytest.mark.parametrize(
    "platform_id,expected_path,is_python",
    [
        ("claude-code", f".claude/pm/{PM_SLUG}.md", False),
        ("gemini-cli", f".gemini/pm/{PM_SLUG}.md", False),
        ("cursor", f".cursor/rules/pm-{PM_SLUG}.md", False),
        ("codex", f".codex/pm/{PM_SLUG}.py", True),
    ],
)
@pytest.mark.no_db
async def test_pm_file_exists_in_zip(
    platform_id: str, expected_path: str, is_python: bool
) -> None:
    """4개 플랫폼 각각에서 ZIP 내 PM 파일이 올바른 경로에 존재하는지 확인."""
    request = GenerateRequest(
        solution={"projectName": "pm-test", "stackPreset": "custom"},
        agents=[],
        skills=[],
        platform={"platformId": platform_id},
    )

    buffer = await generate_zip(
        request,
        "pm-test",
        pm_slug=PM_SLUG,
        pm_markdown=PM_MARKDOWN,
    )

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        assert expected_path in names, (
            f"플랫폼 '{platform_id}': '{expected_path}' 파일이 ZIP에 없음. "
            f"실제 파일 목록: {names}"
        )


@pytest.mark.parametrize(
    "platform_id,expected_path",
    [
        ("claude-code", f".claude/pm/{PM_SLUG}.md"),
        ("gemini-cli", f".gemini/pm/{PM_SLUG}.md"),
        ("cursor", f".cursor/rules/pm-{PM_SLUG}.md"),
        ("codex", f".codex/pm/{PM_SLUG}.py"),
    ],
)
@pytest.mark.no_db
async def test_pm_file_content_includes_markdown(
    platform_id: str, expected_path: str
) -> None:
    """PM 파일 내용에 원본 마크다운이 포함되는지 확인."""
    request = GenerateRequest(
        solution={"projectName": "pm-content-test", "stackPreset": "custom"},
        agents=[],
        skills=[],
        platform={"platformId": platform_id},
    )

    buffer = await generate_zip(
        request,
        "pm-content-test",
        pm_slug=PM_SLUG,
        pm_markdown=PM_MARKDOWN,
    )

    with zipfile.ZipFile(buffer) as zf:
        content = zf.read(expected_path).decode()
        assert "Test PM" in content, f"플랫폼 '{platform_id}': PM 제목이 파일에 없음"
        assert "테스트 PM 프로필" in content, f"플랫폼 '{platform_id}': PM 내용이 파일에 없음"


@pytest.mark.no_db
async def test_codex_pm_uses_python_docstring() -> None:
    """Codex 플랫폼 PM 파일이 Python docstring 래핑인지 확인."""
    request = GenerateRequest(
        solution={"projectName": "codex-pm-test", "stackPreset": "custom"},
        agents=[],
        skills=[],
        platform={"platformId": "codex"},
    )

    buffer = await generate_zip(
        request,
        "codex-pm-test",
        pm_slug=PM_SLUG,
        pm_markdown=PM_MARKDOWN,
    )

    expected_path = f".codex/pm/{PM_SLUG}.py"
    with zipfile.ZipFile(buffer) as zf:
        content = zf.read(expected_path).decode()
        assert '"""' in content, "Codex PM 파일이 Python docstring 형식이 아님"
        assert f"PM Profile: {PM_SLUG}" in content


@pytest.mark.no_db
async def test_no_pm_file_when_slug_not_provided() -> None:
    """pm_slug 없으면 ZIP에 PM 파일이 없어야 한다."""
    request = GenerateRequest(
        solution={"projectName": "no-pm-test", "stackPreset": "custom"},
        agents=[],
        skills=[],
        platform={"platformId": "claude-code"},
    )

    buffer = await generate_zip(request, "no-pm-test")

    with zipfile.ZipFile(buffer) as zf:
        names = zf.namelist()
        pm_files = [n for n in names if "/pm/" in n or "/pm-" in n]
        assert len(pm_files) == 0, f"pm_slug 없는데 PM 파일 생성됨: {pm_files}"


# ── Composition 우선 병합 검증 ──


@pytest.mark.no_db
def test_pm_compositions_agents_merged_into_zip() -> None:
    """composition agent(backend)가 wizard 미선택이어도 api-agent.md 로 emit 되는지 확인."""
    files = emit_files(
        agents=[],
        skills=[],
        pm_slug=PM_SLUG,
        pm_markdown=PM_MARKDOWN,
        pm_compositions=[
            {"component_type": "agent", "component_slug": "backend", "is_required": True},
        ],
        prefetch=build_test_prefetch(agent_slugs=["backend"]),
        project_name="comp-test",
        stack_id="custom",
    )

    assert ".claude/agents/api-agent.md" in files, (
        f"composition backend 에이전트 미emit. 실제: {list(files)}"
    )


@pytest.mark.no_db
def test_pm_compositions_skills_merged_into_zip() -> None:
    """composition skill(tdd)가 wizard 미선택이어도 tdd-smart-coding.md 로 emit 되는지 확인."""
    files = emit_files(
        agents=[],
        skills=[],
        pm_slug=PM_SLUG,
        pm_markdown=PM_MARKDOWN,
        pm_compositions=[
            {"component_type": "skill", "component_slug": "tdd", "is_required": True},
        ],
        prefetch=build_test_prefetch(skill_slugs=["tdd-smart-coding"]),
        project_name="skill-comp-test",
        stack_id="custom",
    )

    assert ".claude/skills/tdd-smart-coding.md" in files, (
        f"composition tdd 스킬 미emit. 실제: {list(files)}"
    )


@pytest.mark.no_db
def test_pm_compositions_merged_with_wizard_no_duplicate() -> None:
    """wizard 선택 + composition 병합 시 중복 없이 emit 되는지 확인 (prefetch 기반)."""
    files = emit_files(
        agents=["backend"],  # 위저드에서도 선택
        skills=["tdd"],
        pm_slug=PM_SLUG,
        pm_markdown=PM_MARKDOWN,
        pm_compositions=[
            {"component_type": "agent", "component_slug": "backend", "is_required": True},
            {"component_type": "agent", "component_slug": "frontend", "is_required": False},
            {"component_type": "skill", "component_slug": "tdd", "is_required": True},
        ],
        prefetch=build_test_prefetch(
            skill_slugs=["tdd-smart-coding"], agent_slugs=["backend", "frontend"]
        ),
        project_name="dedup-test",
        stack_id="custom",
    )

    # backend + frontend 에이전트 + tdd 스킬 모두 포함
    assert ".claude/agents/api-agent.md" in files
    assert ".claude/agents/web-agent.md" in files
    assert ".claude/skills/tdd-smart-coding.md" in files
    # 중복 없음 (files dict 키는 본질적으로 유일하나 emit 경로 회귀 방어)
    agent_files = [n for n in files if n.startswith(".claude/agents/")]
    assert len(set(agent_files)) == len(agent_files), "에이전트 파일 중복 존재"
