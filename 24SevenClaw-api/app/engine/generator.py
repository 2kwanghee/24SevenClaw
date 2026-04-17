"""파일 생성 엔진 — 위저드 설정 기반 프로젝트 파일 생성."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.engine.catalog import (
    find_stack,
    get_env_var_definitions,
    get_selected_agents,
    get_selected_skills,
)
from app.engine.env_generator import generate_env_files
from app.engine.platforms import PlatformDirs, get_platform_dirs

TEMPLATES_DIR = Path(__file__).parent / "templates"

_GUIDE_FILE_MAP: dict[str, str] = {
    "ANTHROPIC_API_KEY": "anthropic-api-key-guide.md",
    "LINEAR_API_KEY": "linear-api-key-guide.md",
    "LINEAR_TEAM_ID": "linear-api-key-guide.md",
    "GEMINI_API_KEY": "gemini-api-key-guide.md",
}

_PLATFORM_COMMANDS_PATH: dict[str, str | None] = {
    "claude-code": ".claude/commands/24SeventStart.md",
    "gemini-cli": ".gemini/commands/24SeventStart.md",
    "cursor": ".cursor/commands/24SeventStart.md",
    "codex": None,
}

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    keep_trailing_newline=True,
    trim_blocks=False,
    lstrip_blocks=False,
)


def _merge_unique(primary: list[str], secondary: list[str]) -> list[str]:
    """primary 먼저, secondary에서 중복 없이 추가."""
    seen = set(primary)
    result = list(primary)
    for item in secondary:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def generate_all(
    *,
    project_name: str,
    project_type: str,
    stack_id: str,
    agent_ids: list[str],
    workflow_ids: list[str],
    platform_id: str = "claude-code",
    env_vars: dict[str, str] | None = None,
    pm_slug: str | None = None,
    pm_markdown: str | None = None,
    pm_compositions: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    """위저드 설정 기반 모든 파일을 생성하여 {relativePath: content} 딕셔너리로 반환."""
    stack = find_stack(stack_id)
    dirs = get_platform_dirs(platform_id)
    files: dict[str, str] = {}

    # PM compositions 우선 병합 — composition의 에이전트/스킬을 우선으로 포함
    if pm_compositions:
        comp_agents = [
            c["component_slug"]
            for c in pm_compositions
            if c.get("component_type") == "agent"
        ]
        comp_skills = [
            c["component_slug"]
            for c in pm_compositions
            if c.get("component_type") == "skill"
        ]
        agent_ids = _merge_unique(comp_agents, agent_ids)
        workflow_ids = _merge_unique(comp_skills, workflow_ids)

    # 에이전트 파일 생성
    _generate_agent_files(files, dirs, project_name, project_type, stack, agent_ids)

    # 스킬 파일 생성
    _generate_skill_files(files, dirs, project_name, project_type, stack, workflow_ids)

    # 루트 가이드 생성 (CLAUDE.md / GEMINI.md 등)
    _generate_root_guide(files, dirs, platform_id, project_name, project_type, stack, agent_ids)

    # settings.json 생성
    _generate_settings(files, dirs, platform_id, workflow_ids)

    # Hook 스크립트 생성
    _generate_hook_files(files, stack, workflow_ids)

    # 자동화 스크립트 생성
    _generate_script_files(files, stack, workflow_ids)

    # .env / .env.example 생성
    _generate_env_files(files, workflow_ids, env_vars or {})

    # PM 파일 주입
    if pm_slug and pm_markdown:
        _generate_pm_files(files, dirs, platform_id, pm_slug, pm_markdown)

    # 온보딩 docs 및 /24SeventStart 커맨드 주입
    _emit_docs(files)
    _emit_start_command(files, platform_id, project_name, workflow_ids)

    return files


def _generate_agent_files(
    files: dict[str, str],
    dirs: PlatformDirs,
    project_name: str,
    project_type: str,
    stack: dict[str, Any] | None,
    agent_ids: list[str],
) -> None:
    """에이전트 .md 파일 생성."""
    agents = get_selected_agents(agent_ids)
    for agent in agents:
        template = _env.get_template(agent["template"])
        content = template.render(
            project_name=project_name,
            project_type=project_type,
            stack=stack,
            agent=agent,
        )
        path = f"{dirs['agent_dir']}/{agent['output_file']}"
        files[path] = content


def _generate_skill_files(
    files: dict[str, str],
    dirs: PlatformDirs,
    project_name: str,
    project_type: str,
    stack: dict[str, Any] | None,
    workflow_ids: list[str],
) -> None:
    """스킬 .md 파일 생성."""
    if not workflow_ids:
        return
    skills = get_selected_skills(workflow_ids)
    skills_dir = f"{dirs['config_dir']}/skills"
    for skill in skills:
        template = _env.get_template(skill["template"])
        content = template.render(
            project_name=project_name,
            project_type=project_type,
            stack=stack,
        )
        path = f"{skills_dir}/{skill['output_file']}"
        files[path] = content


def _get_root_guide_template(platform_id: str) -> str:
    """플랫폼별 루트 가이드 템플릿 파일명 반환."""
    templates: dict[str, str] = {
        "claude-code": "claude.md.j2",
        "gemini-cli": "gemini.md.j2",
        "cursor": "cursor.md.j2",
        "codex": "codex.md.j2",
    }
    return templates.get(platform_id, "claude.md.j2")


def _generate_root_guide(
    files: dict[str, str],
    dirs: PlatformDirs,
    platform_id: str,
    project_name: str,
    project_type: str,
    stack: dict[str, Any] | None,
    agent_ids: list[str],
) -> None:
    """루트 가이드 파일 생성 (CLAUDE.md / GEMINI.md 등)."""
    agents = get_selected_agents(agent_ids)
    agent_refs = [
        {"file": f"{dirs['agent_dir']}/{a['output_file']}", "name": a["name"]}
        for a in agents
    ]

    template_name = _get_root_guide_template(platform_id)
    template = _env.get_template(template_name)
    content = template.render(
        project_name=project_name,
        project_type=project_type,
        stack=stack,
        agent_refs=agent_refs,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d"),
    )
    files[dirs["root_guide"]] = content


def _generate_settings(
    files: dict[str, str],
    dirs: PlatformDirs,
    platform_id: str,
    workflow_ids: list[str],
) -> None:
    """settings.json 생성 — 플랫폼별 설정 형식 분기."""
    if platform_id == "gemini-cli":
        settings = _build_gemini_settings(workflow_ids)
    elif platform_id == "cursor":
        settings = _build_cursor_settings(workflow_ids)
    elif platform_id == "codex":
        settings = _build_codex_settings(workflow_ids)
    else:
        settings = _build_claude_settings(workflow_ids)

    files[dirs["settings_file"]] = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def _build_claude_settings(workflow_ids: list[str]) -> dict[str, Any]:
    """Claude Code용 settings.json 빌드."""
    hooks: dict[str, list[dict[str, str]]] = {
        "UserPromptSubmit": [],
        "PreToolUse": [],
        "PostToolUse": [],
        "Stop": [],
    }

    if "harness-gate" in workflow_ids:
        hooks["UserPromptSubmit"].append(
            {"type": "command", "command": "bash scripts/harness-gate.sh"}
        )

    skills = get_selected_skills(workflow_ids)
    for skill in skills:
        for hook_name in skill["hooks"]:
            if hook_name == "PostToolUse":
                hooks["PostToolUse"].append(
                    {
                        "type": "command",
                        "command": f'echo "🔍 AI 리뷰: {skill["name"]} 검증 중..."',
                    }
                )

    return {
        "permissions": {
            "allow": [
                "Read",
                "Glob",
                "Grep",
                "Edit",
                "Write",
                "Bash(npm run lint:*)",
                "Bash(npm run test:*)",
                "Bash(npx tsc --noEmit)",
            ],
            "deny": [
                "Bash(rm -rf *)",
                "Bash(git push *)",
                "Bash(git checkout main)",
            ],
        },
        "hooks": hooks,
    }


def _build_gemini_settings(workflow_ids: list[str]) -> dict[str, Any]:
    """Gemini CLI용 settings.json 빌드."""
    settings: dict[str, Any] = {
        "coreTools": ["file_edit", "file_read", "shell", "web_search"],
        "safetySettings": {
            "denyPatterns": [
                "rm -rf *",
                "git push *",
                "git checkout main",
            ],
        },
    }

    if "harness-gate" in workflow_ids:
        settings["prePromptHook"] = "bash scripts/harness-gate.sh"

    return settings


def _build_cursor_settings(workflow_ids: list[str]) -> dict[str, Any]:
    """Cursor용 settings.json 빌드."""
    settings: dict[str, Any] = {
        "rules": {
            "source": "project",
            "file": ".cursorrules",
        },
        "safetySettings": {
            "denyPatterns": [
                "rm -rf *",
                "git push *",
                "git checkout main",
            ],
        },
    }

    if "harness-gate" in workflow_ids:
        settings["preCommandHook"] = "bash scripts/harness-gate.sh"

    return settings


def _build_codex_settings(workflow_ids: list[str]) -> dict[str, Any]:
    """Codex용 settings.json 빌드."""
    settings: dict[str, Any] = {
        "safetySettings": {
            "denyPatterns": [
                "rm -rf *",
                "git push *",
                "git checkout main",
            ],
        },
    }

    if "harness-gate" in workflow_ids:
        settings["preCommandHook"] = "bash scripts/harness-gate.sh"

    return settings


def _generate_hook_files(
    files: dict[str, str],
    stack: dict[str, Any] | None,
    workflow_ids: list[str],
) -> None:
    """harness-gate.sh Hook 스크립트 생성."""
    if "harness-gate" not in workflow_ids:
        return

    template = _env.get_template("hooks/harness-gate.sh.j2")
    content = template.render(stack=stack)
    files["scripts/harness-gate.sh"] = content


def _generate_script_files(
    files: dict[str, str],
    stack: dict[str, Any] | None,
    workflow_ids: list[str],
) -> None:
    """워크플로우별 자동화 스크립트 생성."""
    if not workflow_ids:
        return

    if "ralph-loop" in workflow_ids:
        files[".ralph/fix_plan.md"] = """# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P0: 긴급

## P1: 높음

## P2: 기능 요구사항

- [ ] **첫 번째 태스크를 여기에 작성하세요**
  > 상세 설명

---

## 진행 로그

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
"""

    has_test_workflow = "tdd" in workflow_ids or "harness-gate" in workflow_ids
    if has_test_workflow and stack and stack["id"] != "custom":
        lines = [
            "#!/usr/bin/env bash",
            "# 전체 테스트 실행 스크립트",
            "set -euo pipefail",
            "",
        ]
        if stack["test"]["backend"]:
            lines.extend(["echo '🧪 백엔드 테스트...'", stack["test"]["backend"], ""])
        if stack["test"]["frontend"]:
            lines.extend(["echo '🧪 프론트엔드 테스트...'", stack["test"]["frontend"], ""])
        lines.append('echo "✅ 모든 테스트 통과"')
        files["scripts/run-tests.sh"] = "\n".join(lines) + "\n"


def _generate_pm_files(
    files: dict[str, str],
    dirs: PlatformDirs,
    platform_id: str,
    pm_slug: str,
    pm_markdown: str,
) -> None:
    """플랫폼별 PM 파일 생성 — Jinja2 템플릿 기반."""
    template_map: dict[str, tuple[str, str]] = {
        "claude-code": (
            "pm/pm-claude.md.j2",
            f"{dirs['pm_dir']}/{pm_slug}.md",
        ),
        "gemini-cli": (
            "pm/pm-gemini.md.j2",
            f"{dirs['pm_dir']}/{pm_slug}.md",
        ),
        "cursor": (
            "pm/pm-cursor.md.j2",
            f"{dirs['pm_dir']}/pm-{pm_slug}.md",
        ),
        "codex": (
            "pm/pm-codex.py.j2",
            f"{dirs['pm_dir']}/{pm_slug}.py",
        ),
    }
    template_name, output_path = template_map.get(platform_id, template_map["claude-code"])
    template = _env.get_template(template_name)
    content = template.render(pm_slug=pm_slug, pm_markdown=pm_markdown)
    files[output_path] = content


def generate_pm_files(
    pm_slug: str,
    pm_markdown: str,
    platform_id: str = "claude-code",
) -> dict[str, str]:
    """선택된 PM 프로필을 플랫폼별 파일로 주입한다. (하위 호환성 유지)

    생성 경로:
        claude-code → .claude/pm/{slug}.md
        gemini-cli  → .gemini/pm/{slug}.md
        cursor      → .cursor/rules/pm-{slug}.md
        codex       → .codex/pm/{slug}.py (Python docstring 래핑)
        기타         → .claude/pm/{slug}.md (claude-code 기본)
    """
    dirs = get_platform_dirs(platform_id)
    files: dict[str, str] = {}
    _generate_pm_files(files, dirs, platform_id, pm_slug, pm_markdown)
    return files


def _generate_env_files(
    files: dict[str, str],
    workflow_ids: list[str],
    env_vars: dict[str, str],
) -> None:
    """스킬별 API 키 매핑 기반 .env / .env.example 생성."""
    env_var_definitions = get_env_var_definitions(workflow_ids)

    # 카탈로그 정의가 없고 사용자 입력도 없으면 스킵
    if not env_var_definitions and not env_vars:
        return

    env_files = generate_env_files(
        env_var_definitions=env_var_definitions,
        env_vars=env_vars,
    )
    files.update(env_files)


def _emit_docs(files: dict[str, str]) -> None:
    """docs/api-keys/*.md 정적 가이드 문서를 ZIP에 포함."""
    docs_src = TEMPLATES_DIR / "docs" / "api-keys"
    for doc_file in sorted(docs_src.glob("*.md")):
        files[f"docs/api-keys/{doc_file.name}"] = doc_file.read_text(encoding="utf-8")


def _emit_start_command(
    files: dict[str, str],
    platform_id: str,
    project_name: str,
    workflow_ids: list[str],
) -> None:
    """/24SeventStart 온보딩 커맨드 파일을 플랫폼별 경로로 생성."""
    output_path = _PLATFORM_COMMANDS_PATH.get(platform_id)
    if output_path is None:
        return

    env_var_definitions = get_env_var_definitions(workflow_ids)
    required_vars = [
        {
            "name": v["name"],
            "description": v.get("description", ""),
            "guide_file": _GUIDE_FILE_MAP.get(v["name"], "anthropic-api-key-guide.md"),
        }
        for v in env_var_definitions
        if v.get("required") and v["name"] != "ANTHROPIC_API_KEY"
    ]

    template = _env.get_template("commands/24seven-start.md.j2")
    content = template.render(
        project_name=project_name,
        required_vars=required_vars,
        has_ralph="ralph-loop" in workflow_ids,
        has_linear="linear" in workflow_ids,
    )
    files[output_path] = content
