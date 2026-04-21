"""??일 ??성 ??진 ??????????정 기반 ??로??트 ??일 ??성."""

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
    """primary 먼??, secondary??서 중복 ??이 추??."""
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
    """????????정 기반 모든 ??일????성??여 {relativePath: content} ??셔??리??반환."""
    stack = find_stack(stack_id)
    dirs = get_platform_dirs(platform_id)
    files: dict[str, str] = {}

    # PM compositions ??선 병합 ??composition????이??트/??킬????선??로 ??함
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

    # ??이??트 ??일 ??성
    _generate_agent_files(files, dirs, project_name, project_type, stack, agent_ids)

    # ??킬 ??일 ??성
    _generate_skill_files(files, dirs, project_name, project_type, stack, workflow_ids)

    # 루트 가??드 ??성 (CLAUDE.md / GEMINI.md ??
    _generate_root_guide(files, dirs, platform_id, project_name, project_type, stack, agent_ids)

    # settings.json ??성
    _generate_settings(files, dirs, platform_id, workflow_ids)

    # Hook ??크립트 ??성
    _generate_hook_files(files, stack, workflow_ids)

    # ??동????크립트 ??성
    _generate_script_files(files, stack, workflow_ids)

    # Linear webhook ??크립트 ??성 (linear ??킬 ??택 ??
    if "linear" in workflow_ids:
        _generate_webhook_files(files, project_name)

    # .env / .env.example ??성
    _generate_env_files(files, workflow_ids, env_vars or {})

    # PM ??일 주입
    if pm_slug and pm_markdown:
        _generate_pm_files(files, dirs, platform_id, pm_slug, pm_markdown)

    # ??보??docs ??/24SeventStart 커맨??주입
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
    """??이??트 .md ??일 ??성."""
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
    """??킬 .md ??일 ??성."""
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
    """??랫??별 루트 가??드 ??플????일??반환."""
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
    """루트 가??드 ??일 ??성 (CLAUDE.md / GEMINI.md ??."""
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
    """settings.json ??성 ????랫??별 ??정 ??식 분기."""
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
    """Claude Code??settings.json 빌드."""
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
                        "command": f'echo "??? AI 리뷰: {skill["name"]} 검????.."',
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
    """Gemini CLI??settings.json 빌드."""
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
    """Cursor??settings.json 빌드."""
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
    """Codex??settings.json 빌드."""
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
    """harness-gate.sh Hook ??크립트 ??성."""
    if "harness-gate" not in workflow_ids:
        return

    template = _env.get_template("hooks/harness-gate.sh.j2")
    content = template.render(stack=stack)
    files["scripts/harness-gate.sh"] = content


def _generate_webhook_files(
    files: dict[str, str],
    project_name: str,
) -> None:
    """Linear webhook ??신 ??버 + ??링 ??백 ??크립트 ??성."""
    ctx = {"project_name": project_name}

    for tmpl_path, out_path in [
        ("scripts/webhook_server.py.j2", "scripts/webhook_server.py"),
        ("scripts/linear_watcher.py.j2", "scripts/linear_watcher.py"),
        ("scripts/start-webhook.sh.j2", "scripts/start-webhook.sh"),
        ("scripts/setup-tunnel.sh.j2", "scripts/setup-tunnel.sh"),
    ]:
        tpl = _env.get_template(tmpl_path)
        files[out_path] = tpl.render(**ctx)

    docs_src = TEMPLATES_DIR / "docs" / "webhook" / "WEBHOOK_SETUP.md.j2"
    if docs_src.exists():
        tpl = _env.get_template("docs/webhook/WEBHOOK_SETUP.md.j2")
        files["docs/WEBHOOK_SETUP.md"] = tpl.render(**ctx)


def _generate_script_files(
    files: dict[str, str],
    stack: dict[str, Any] | None,
    workflow_ids: list[str],
) -> None:
    """??크??로??별 ??동????크립트 ??성."""
    if not workflow_ids:
        return

    if "ralph-loop" in workflow_ids:
        files[".ralph/fix_plan.md"] = """# Ralph Loop ????업 ??(Fix Plan)

> Claude가 ????일????고 미완??`- [ ]`) ??????처리??다.
> ??료 ??`- [x]`????시??고 커밋??다.
> `- [!]`??건너?????? (??유 기록 ??수).

---

## P0: 긴급

## P1: ??음

## P2: 기능 ??구??항

- [ ] **??번째 ??스???? ??기????성??세??*
  > ??세 ??명

---

## 진행 로그

| ??각 | ???? | ??태 | 비고 |
|------|------|------|------|
"""

    has_test_workflow = "tdd" in workflow_ids or "harness-gate" in workflow_ids
    if has_test_workflow and stack and stack["id"] != "custom":
        lines = [
            "#!/usr/bin/env bash",
            "# ??체 ??스????행 ??크립트",
            "set -euo pipefail",
            "",
        ]
        if stack["test"]["backend"]:
            lines.extend(["echo '??? 백엔????스??..'", stack["test"]["backend"], ""])
        if stack["test"]["frontend"]:
            lines.extend(["echo '??? ??론??엔????스??..'", stack["test"]["frontend"], ""])
        lines.append('echo "??모든 ??스????과"')
        files["scripts/run-tests.sh"] = "\n".join(lines) + "\n"


def _generate_pm_files(
    files: dict[str, str],
    dirs: PlatformDirs,
    platform_id: str,
    pm_slug: str,
    pm_markdown: str,
) -> None:
    """??랫??별 PM ??일 ??성 ??Jinja2 ??플??기반."""
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
    """??택??PM ??로??을 ??랫??별 ??일??주입??다. (??위 ??환??????)

    ??성 경로:
        claude-code ??.claude/pm/{slug}.md
        gemini-cli  ??.gemini/pm/{slug}.md
        cursor      ??.cursor/rules/pm-{slug}.md
        codex       ??.codex/pm/{slug}.py (Python docstring ??핑)
        기??         ??.claude/pm/{slug}.md (claude-code 기본)
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
    """??킬??API ??매핑 기반 .env / .env.example ??성."""
    env_var_definitions = get_env_var_definitions(workflow_ids)

    # 카탈로그 ??의가 ??고 ??용????력????으????킵
    if not env_var_definitions and not env_vars:
        return

    env_files = generate_env_files(
        env_var_definitions=env_var_definitions,
        env_vars=env_vars,
    )
    files.update(env_files)


def _emit_docs(files: dict[str, str]) -> None:
    """docs/api-keys/*.md ??적 가??드 문서??ZIP????함."""
    docs_src = TEMPLATES_DIR / "docs" / "api-keys"
    for doc_file in sorted(docs_src.glob("*.md")):
        files[f"docs/api-keys/{doc_file.name}"] = doc_file.read_text(encoding="utf-8")


def _emit_start_command(
    files: dict[str, str],
    platform_id: str,
    project_name: str,
    workflow_ids: list[str],
) -> None:
    """/24SeventStart ??보??커맨????일????랫??별 경로????성."""
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

    template = _env.get_template("commands/clickeye-start.md.j2")
    content = template.render(
        project_name=project_name,
        required_vars=required_vars,
        has_ralph="ralph-loop" in workflow_ids,
        has_linear="linear" in workflow_ids,
    )
    files[output_path] = content

