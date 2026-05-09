"""파일 생성 엔진 — 위저드 설정 기반 프로젝트 파일 생성."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from app.engine.catalog import (
    CatalogPrefetch,
    find_stack,
    get_env_var_definitions,
    get_selected_agents,
    get_selected_hooks,
    get_selected_skills,
)
from app.engine.env_generator import generate_env_files
from app.engine.platforms import PlatformDirs, get_platform_dirs
from app.engine.pptx_generator import build_setup_guide_pptx

TEMPLATES_DIR = Path(__file__).parent / "templates"

_GUIDE_FILE_MAP: dict[str, str] = {
    "ANTHROPIC_API_KEY": "anthropic-api-key-guide.md",
    "LINEAR_API_KEY": "linear-api-key-guide.md",
    "LINEAR_TEAM_ID": "linear-api-key-guide.md",
    "GEMINI_API_KEY": "gemini-api-key-guide.md",
}

_PLATFORM_COMMANDS_PATH: dict[str, str | None] = {
    "claude-code": ".claude/commands/ClickEyeStart.md",
    "gemini-cli": ".gemini/commands/ClickEyeStart.md",
    "cursor": ".cursor/commands/ClickEyeStart.md",
    "codex": None,
}

_PLATFORM_REMOVE_COMMANDS_PATH: dict[str, str | None] = {
    "claude-code": ".claude/commands/ClickEyeRemove.md",
    "gemini-cli": ".gemini/commands/ClickEyeRemove.md",
    "cursor": ".cursor/commands/ClickEyeRemove.md",
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
    os_id: str = "wsl2",
    env_vars: dict[str, str] | None = None,
    pm_slug: str | None = None,
    pm_markdown: str | None = None,
    pm_compositions: list[dict[str, Any]] | None = None,
    catalog_entry: dict[str, Any] | None = None,
    catalog_prefetch: CatalogPrefetch | None = None,
    hook_ids: list[str] | None = None,
    clickeye_vars: dict[str, str] | None = None,
    enable_auto_decompose: bool = False,
    auth_method: str = "api_key",
) -> dict[str, str | bytes]:
    """?ì????¤ì  ê¸°ë° ëª¨ë  ?ì¼???ì±?ì¬ {relativePath: content} ?ì?ë¦¬ë¡?ë°í."""
    stack = find_stack(stack_id)
    dirs = get_platform_dirs(platform_id)
    files: dict[str, str | bytes] = {}

    # PM compositions ?°ì  ë³í© ??composition???ì´?í¸/?¤í¬???°ì ?¼ë¡ ?¬í¨
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

    # ?ì´?í¸ ?ì¼ ?ì±
    _generate_agent_files(files, dirs, project_name, project_type, stack, agent_ids, catalog_prefetch)

    # ?¤í¬ ?ì¼ ?ì±
    _generate_skill_files(files, dirs, project_name, project_type, stack, workflow_ids, catalog_prefetch)

    # ë£¨í¸ ê°?´ë ?ì± (CLAUDE.md / GEMINI.md ??
    _generate_root_guide(
        files, dirs, platform_id, project_name, project_type, stack, agent_ids, catalog_entry, catalog_prefetch
    )

    # settings.json ?ì±
    _generate_settings(files, dirs, platform_id, workflow_ids, catalog_prefetch)

    # Hook ?¤í¬ë¦½í¸ ?ì±
    _generate_hook_files(files, stack, workflow_ids, catalog_prefetch, hook_ids)

    # ?ë???¤í¬ë¦½í¸ ?ì±
    _generate_script_files(files, stack, workflow_ids)

    # Linear webhook ?¤í¬ë¦½í¸ ?ì± (linear ?¤í¬ ? í ??
    if "linear" in workflow_ids:
        _generate_webhook_files(files, project_name, dirs["config_dir"])

    # .env / .env.example ?ì±
    _generate_env_files(files, workflow_ids, env_vars or {}, catalog_prefetch, clickeye_vars)

    # PM ?ì¼ ì£¼ì
    if pm_slug and pm_markdown:
        _generate_pm_files(files, dirs, platform_id, pm_slug, pm_markdown, catalog_entry)

    # 온보딩 docs 및 /ClickEyeStart 커맨드 주입
    _emit_docs(files)
    _emit_start_command(files, platform_id, project_name, workflow_ids, catalog_prefetch)
    _emit_remove_command(files, platform_id, project_name)
    _emit_setup_guide_pptx(files, project_name, pm_slug or "", workflow_ids, platform_id)
    _emit_first_run_artifacts(
        files, platform_id, os_id, workflow_ids, project_name,
        enable_auto_decompose=enable_auto_decompose,
        auth_method=auth_method,
    )

    return files


def _generate_agent_files(
    files: dict[str, str | bytes],
    dirs: PlatformDirs,
    project_name: str,
    project_type: str,
    stack: dict[str, Any] | None,
    agent_ids: list[str],
    catalog_prefetch: CatalogPrefetch | None = None,
) -> None:
    """에이전트 .md 파일 생성."""
    agents = get_selected_agents(agent_ids, catalog_prefetch)
    for agent in agents:
        if not agent.get("output_file"):
            continue
        ctx = dict(project_name=project_name, project_type=project_type, stack=stack, agent=agent)
        if agent.get("body_md"):
            rendered = _env.from_string(agent["body_md"]).render(**ctx)
        elif agent.get("template"):
            try:
                rendered = _env.get_template(agent["template"]).render(**ctx)
            except Exception:
                continue
        else:
            continue
        path = f"{dirs['agent_dir']}/{agent['output_file']}"
        files[path] = rendered


def _generate_skill_files(
    files: dict[str, str | bytes],
    dirs: PlatformDirs,
    project_name: str,
    project_type: str,
    stack: dict[str, Any] | None,
    workflow_ids: list[str],
    catalog_prefetch: CatalogPrefetch | None = None,
) -> None:
    """스킬 .md 파일 생성."""
    if not workflow_ids:
        return
    skills = get_selected_skills(workflow_ids, catalog_prefetch)
    skills_dir = f"{dirs['config_dir']}/skills"
    for skill in skills:
        if not skill.get("output_file"):
            continue
        ctx = dict(project_name=project_name, project_type=project_type, stack=stack)
        if skill.get("body_md"):
            rendered = _env.from_string(skill["body_md"]).render(**ctx)
        elif skill.get("template"):
            try:
                rendered = _env.get_template(skill["template"]).render(**ctx)
            except Exception:
                continue
        else:
            continue
        path = f"{skills_dir}/{skill['output_file']}"
        files[path] = rendered


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
    files: dict[str, str | bytes],
    dirs: PlatformDirs,
    platform_id: str,
    project_name: str,
    project_type: str,
    stack: dict[str, Any] | None,
    agent_ids: list[str],
    catalog_entry: dict[str, Any] | None = None,
    catalog_prefetch: CatalogPrefetch | None = None,
) -> None:
    """루트 가이드 파일 생성 (CLAUDE.md / GEMINI.md 등)."""
    agents = get_selected_agents(agent_ids, catalog_prefetch)
    agent_refs = [
        {"file": f"{dirs['agent_dir']}/{a['output_file']}", "name": a.get("label", a.get("name", a["id"]))}
        for a in agents if a.get("output_file")
    ]

    template_name = _get_root_guide_template(platform_id)
    template = _env.get_template(template_name)
    content = template.render(
        project_name=project_name,
        project_type=project_type,
        stack=stack,
        agent_refs=agent_refs,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d"),
        catalog_entry=catalog_entry,
    )
    files[dirs["root_guide"]] = content


def _generate_settings(
    files: dict[str, str | bytes],
    dirs: PlatformDirs,
    platform_id: str,
    workflow_ids: list[str],
    catalog_prefetch: CatalogPrefetch | None = None,
) -> None:
    """settings.json 생성 — 플랫폼별 설정 형식 분기."""
    if platform_id == "gemini-cli":
        settings = _build_gemini_settings(workflow_ids)
    elif platform_id == "cursor":
        settings = _build_cursor_settings(workflow_ids)
    elif platform_id == "codex":
        settings = _build_codex_settings(workflow_ids)
    else:
        settings = _build_claude_settings(workflow_ids, catalog_prefetch)

    files[dirs["settings_file"]] = json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def _build_claude_settings(
    workflow_ids: list[str],
    catalog_prefetch: CatalogPrefetch | None = None,
) -> dict[str, Any]:
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

    skills = get_selected_skills(workflow_ids, catalog_prefetch)
    for skill in skills:
        for hook_name in skill.get("hook_events", skill.get("hooks", [])):
            if hook_name == "PostToolUse":
                hooks["PostToolUse"].append(
                    {
                        "type": "command",
                        "command": f'echo "🔍 AI 리뷰: {skill["name"]} 검증 중.."',
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
    files: dict[str, str | bytes],
    stack: dict[str, Any] | None,
    workflow_ids: list[str],
    catalog_prefetch: CatalogPrefetch | None = None,
    hook_ids: list[str] | None = None,
) -> None:
    """Hook 스크립트 생성 — harness-gate.sh 및 DB 훅."""
    if "harness-gate" in workflow_ids:
        template = _env.get_template("hooks/harness-gate.sh.j2")
        content = template.render(stack=stack)
        files["scripts/harness-gate.sh"] = content

    if hook_ids and catalog_prefetch:
        hooks = get_selected_hooks(hook_ids, catalog_prefetch)
        for hook in hooks:
            if hook.get("output_file") and hook.get("body_md"):
                ctx = dict(stack=stack)
                rendered = _env.from_string(hook["body_md"]).render(**ctx)
                files[f"scripts/{hook['output_file']}"] = rendered


def _generate_webhook_files(
    files: dict[str, str | bytes],
    project_name: str,
    config_dir: str = ".claude",
) -> None:
    """Linear webhook 수신 서버 + 이링 이백 스크립트 생성."""
    ctx = {"project_name": project_name, "config_dir": config_dir}

    for tmpl_path, out_path in [
        ("scripts/webhook_server.py.j2", "scripts/webhook_server.py"),
        ("scripts/linear_watcher.py.j2", "scripts/linear_watcher.py"),
        ("scripts/start-webhook.sh.j2", "scripts/start-webhook.sh"),
        ("scripts/setup-tunnel.sh.j2", "scripts/setup-tunnel.sh"),
        ("scripts/run-pipeline.sh.j2", "scripts/run-pipeline.sh"),
        ("scripts/register-webhook.py.j2", "scripts/register-webhook.py"),
    ]:
        tpl = _env.get_template(tmpl_path)
        files[out_path] = tpl.render(**ctx)

    docs_src = TEMPLATES_DIR / "docs" / "webhook" / "WEBHOOK_SETUP.md.j2"
    if docs_src.exists():
        tpl = _env.get_template("docs/webhook/WEBHOOK_SETUP.md.j2")
        files["docs/WEBHOOK_SETUP.md"] = tpl.render(**ctx)


def _generate_script_files(
    files: dict[str, str | bytes],
    stack: dict[str, Any] | None,
    workflow_ids: list[str],
) -> None:
    """플랫폼별 자동화 스크립트 생성."""
    if not workflow_ids:
        return

    if "ralph-loop" in workflow_ids:
        files[".ralph/fix_plan.md"] = """# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뀐 항목 (사유 기록 필수).

---

## P0: 긴급

## P1: 다음

## P2: 기능 요구사항

- [ ] **첫 번째 작업을 여기에 작성하세요**
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
            "# ?ì²´ ?ì¤???¤í ?¤í¬ë¦½í¸",
            "set -euo pipefail",
            "",
        ]
        if stack["test"]["backend"]:
            lines.extend(["echo '🧪 백엔드 테스트..'", stack["test"]["backend"], ""])
        if stack["test"]["frontend"]:
            lines.extend(["echo '🧪 프론트엔드 테스트..'", stack["test"]["frontend"], ""])
        lines.append('echo "✅ 모든 테스트 통과"')
        files["scripts/run-tests.sh"] = "\n".join(lines) + "\n"


def _generate_pm_files(
    files: dict[str, str | bytes],
    dirs: PlatformDirs,
    platform_id: str,
    pm_slug: str,
    pm_markdown: str,
    catalog_entry: dict[str, Any] | None = None,
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
    content = template.render(pm_slug=pm_slug, pm_markdown=pm_markdown, catalog_entry=catalog_entry)
    files[output_path] = content


def generate_pm_files(
    pm_slug: str,
    pm_markdown: str,
    platform_id: str = "claude-code",
) -> dict[str, str | bytes]:
    """? í??PM ?ë¡?ì ?ë«?¼ë³ ?ì¼ë¡?ì£¼ì?ë¤. (?ì ?¸í??? ì?)

    ?ì± ê²½ë¡:
        claude-code ??.claude/pm/{slug}.md
        gemini-cli  ??.gemini/pm/{slug}.md
        cursor      ??.cursor/rules/pm-{slug}.md
        codex       ??.codex/pm/{slug}.py (Python docstring ?í)
        ê¸°í?         ??.claude/pm/{slug}.md (claude-code ê¸°ë³¸)
    """
    dirs = get_platform_dirs(platform_id)
    files: dict[str, str | bytes] = {}
    _generate_pm_files(files, dirs, platform_id, pm_slug, pm_markdown)
    return files


def _generate_env_files(
    files: dict[str, str | bytes],
    workflow_ids: list[str],
    env_vars: dict[str, str],
    catalog_prefetch: CatalogPrefetch | None = None,
    clickeye_vars: dict[str, str] | None = None,
) -> None:
    """스킬별 API 키 매핑 기반 .env / .env.example 생성."""
    env_var_definitions = get_env_var_definitions(workflow_ids, catalog_prefetch)

    # ì¹´íë¡ê·¸ ?ìê° ?ê³  ?¬ì©???ë ¥???ì¼ë©??¤íµ
    if not env_var_definitions and not env_vars and not clickeye_vars:
        return

    env_files: dict[str, str]
    if env_var_definitions or env_vars:
        env_files = generate_env_files(
            env_var_definitions=env_var_definitions,
            env_vars=env_vars,
        )
    else:
        # clickeye_vars만 있을 때 — 최소 베이스 파일 생성
        env_files = {
            ".env": "# 환경 변수 — 이 파일을 .gitignore에 추가하세요\n# 자동 생성됨 (ClickEye)\n",
            ".env.example": "# 환경 변수 템플릿 — 복사하여 .env로 사용\n# cp .env.example .env\n",
        }

    if clickeye_vars:
        clickeye_env_section = (
            "\n# ── ClickEye 클라우드 연동 (최초 셋업에만 사용, 완료 후 토큰은 만료됨) ──\n"
            + "\n".join(f"{k}={v}" for k, v in clickeye_vars.items())
            + "\n"
        )
        clickeye_example_section = (
            "\n# ── ClickEye 클라우드 연동 (최초 셋업에만 사용, 완료 후 토큰은 만료됨) ──\n"
            + "\n".join(f"{k}=" for k in clickeye_vars)
            + "\n"
        )
        if ".env" in env_files:
            env_files[".env"] = str(env_files[".env"]) + clickeye_env_section
        if ".env.example" in env_files:
            env_files[".env.example"] = str(env_files[".env.example"]) + clickeye_example_section

    files.update(env_files)


def _emit_setup_guide_pptx(
    files: dict[str, str | bytes],
    project_name: str,
    pm_slug: str,
    workflow_ids: list[str],
    platform_id: str,
) -> None:
    """가이드 PPTX를 생성해 docs/setup-guide.pptx 로 ZIP에 포함."""
    try:
        pptx_bytes = build_setup_guide_pptx(
            project_name=project_name,
            pm_slug=pm_slug,
            has_linear="linear" in workflow_ids,
            platform=platform_id,
        )
        files["docs/setup-guide.pptx"] = pptx_bytes
    except Exception:
        pass  # PPTX 생성 실패 시 ZIP은 정상 반환


def _emit_docs(files: dict[str, str | bytes]) -> None:
    """docs/api-keys/*.md 정적 가이드 문서를 ZIP에 포함."""
    docs_src = TEMPLATES_DIR / "docs" / "api-keys"
    for doc_file in sorted(docs_src.glob("*.md")):
        files[f"docs/api-keys/{doc_file.name}"] = doc_file.read_text(encoding="utf-8")


def _emit_start_command(
    files: dict[str, str | bytes],
    platform_id: str,
    project_name: str,
    workflow_ids: list[str],
    catalog_prefetch: CatalogPrefetch | None = None,
) -> None:
    """/ClickEyeStart 온보딩 커맨드 파일을 플랫폼별 경로로 생성."""
    output_path = _PLATFORM_COMMANDS_PATH.get(platform_id)
    if output_path is None:
        return

    env_var_definitions = get_env_var_definitions(workflow_ids, catalog_prefetch)
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


def _emit_remove_command(
    files: dict[str, str | bytes],
    platform_id: str,
    project_name: str,
) -> None:
    """/ClickEyeRemove 커맨드 파일을 플랫폼별 경로로 생성."""
    output_path = _PLATFORM_REMOVE_COMMANDS_PATH.get(platform_id)
    if output_path is None:
        return

    template = _env.get_template("commands/clickeye-remove.md.j2")
    content = template.render(project_name=project_name)
    files[output_path] = content


def _emit_first_run_artifacts(
    files: dict[str, str | bytes],
    platform_id: str,
    os_id: str,
    workflow_ids: list[str],
    project_name: str,
    *,
    enable_auto_decompose: bool = False,
    auth_method: str = "api_key",
) -> None:
    """first-run 런처(start.sh)와 README.md를 ZIP에 포함.

    WSL2/Linux 환경에서 자동 감지·설치를 지원한다.
    pptx 생성과 동일하게 예외 발생 시 ZIP 반환은 정상 처리된다.
    """
    try:
        ctx = {
            "project_name": project_name,
            "platform_id": platform_id,
            "os_id": os_id,
            "has_linear": "linear" in workflow_ids,
            "enable_auto_decompose": enable_auto_decompose,
            "auth_method": auth_method,
        }
        launcher = _env.get_template("start.sh.j2")
        files["start.sh"] = launcher.render(**ctx)

        remover = _env.get_template("remove.sh.j2")
        files["remove.sh"] = remover.render(**ctx)

        readme = _env.get_template("README.md.j2")
        files["README.md"] = readme.render(**ctx)

        # stop.sh — 원클릭 종료
        stopper = _env.get_template("stop.sh.j2")
        files["stop.sh"] = stopper.render(**ctx)

        # systemd 서비스 스크립트 (WSL2 환경)
        if os_id in ("wsl2", "linux"):
            install_svc = _env.get_template("scripts/install-service.sh.j2")
            files["scripts/install-service.sh"] = install_svc.render(**ctx)
            uninstall_svc = _env.get_template("scripts/uninstall-service.sh.j2")
            files["scripts/uninstall-service.sh"] = uninstall_svc.render(**ctx)

        # Windows Task Scheduler 자동 시작 스크립트
        autostart = _env.get_template("scripts/setup-autostart.ps1.j2")
        files["scripts/setup-autostart.ps1"] = autostart.render(**ctx)

        # 부트스트랩 스크립트 — 자동 분해 ON 시에만 ZIP에 포함
        if enable_auto_decompose:
            bootstrap_sh = _env.get_template("scripts/bootstrap_clickeye.sh.j2")
            files["scripts/bootstrap_clickeye.sh"] = bootstrap_sh.render(**ctx)
            decompose_py = _env.get_template("scripts/decompose_local.py.j2")
            files["scripts/decompose_local.py"] = decompose_py.render(**ctx)
            push_linear_py = _env.get_template("scripts/push_to_linear_local.py.j2")
            files["scripts/push_to_linear_local.py"] = push_linear_py.render(**ctx)

        # API 키 갱신 스크립트 (항상 포함)
        refresh_sh = _env.get_template("scripts/refresh-env.sh.j2")
        files["scripts/refresh-env.sh"] = refresh_sh.render(**ctx)
        scripts_readme = _env.get_template("scripts/README.md.j2")
        files["scripts/README.md"] = scripts_readme.render(**ctx)

        # log/, .run/ 디렉토리 자리 확보 (.gitkeep)
        files["logs/.gitkeep"] = ""
        files[".run/.gitkeep"] = ""
    except Exception:
        import logging as _logging
        _logging.getLogger(__name__).exception("_emit_first_run_artifacts 실패")
