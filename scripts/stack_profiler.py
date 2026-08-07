#!/usr/bin/env python3
"""스택 프로파일러 (파생형 하네스 Tier 1) — 대상 레포의 빌드 스택을 결정론적으로 감지.

LLM·네트워크 접근 없음. Python 3 표준 라이브러리만 사용. 완전 결정론적이다
(동일 입력 → 동일 출력). 감지하지 못한 명령은 **null**로 남긴다(추측 금지).

루트(`.`)와 1-depth 하위 디렉터리(모노레포 대응)를 스캔해 매니페스트를 찾는다:
  - package.json      → Node (scripts의 test/lint/build, next/react 등 프레임워크)
  - pyproject.toml    → Python (pytest/ruff, uv/poetry 판별)
  - requirements.txt  → Python (pyproject 없을 때만)
  - go.mod            → Go
  - Cargo.toml        → Rust
  - docker-compose*.yml → 인프라(명령 없음 — 존재만 기록)

산출(--out, 기본 <repo>/.claude/):
  a. harness-profile.json — 기계 판독용 스택 프로파일
  b. CLAUDE.stack.md      — 사람/에이전트 판독용 규약 프래그먼트(스택별 명령 표)
  c. gates 파일           — delivery_verifier 의 VERIFY_GATES_FILE 형식(줄당 1명령,
                            # 주석 허용). 감지된 test/lint 를 게이트 후보로 기록.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - 구버전 폴백
    tomllib = None  # type: ignore[assignment]

PROFILE_VERSION = 1


# ── TOML 로드 (tomllib 우선, 없으면 경량 텍스트 스캔) ─────────────────────────


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _load_toml(path: str) -> dict[str, Any]:
    """tomllib 이 있으면 정식 파싱, 없으면 빈 dict(→ 텍스트 스캔 폴백 사용)."""
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    except (OSError, ValueError):
        return {}


# ── Node (package.json) ──────────────────────────────────────────────────────


def _detect_package_manager_node(dir_path: str, pkg: dict[str, Any]) -> str:
    # packageManager 필드(예: "pnpm@9.0.0") 우선
    pm_field = pkg.get("packageManager")
    if isinstance(pm_field, str) and "@" in pm_field:
        name = pm_field.split("@", 1)[0].strip()
        if name in {"pnpm", "yarn", "npm", "bun"}:
            return name
    # 락파일로 판별
    lockmap = [
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("bun.lockb", "bun"),
        ("package-lock.json", "npm"),
    ]
    for lockfile, pm in lockmap:
        if os.path.exists(os.path.join(dir_path, lockfile)):
            return pm
    return "npm"


def _detect_framework_node(deps: dict[str, Any]) -> str | None:
    # 구체적인 것부터 — 첫 매치를 채택(결정론적 순서)
    candidates = [
        ("next", "next"),
        ("@angular/core", "angular"),
        ("nuxt", "nuxt"),
        ("svelte", "svelte"),
        ("vue", "vue"),
        ("@nestjs/core", "nestjs"),
        ("react", "react"),
        ("express", "express"),
    ]
    for key, name in candidates:
        if key in deps:
            return name
    return None


def _profile_node(rel_path: str, dir_path: str) -> dict[str, Any] | None:
    pkg_path = os.path.join(dir_path, "package.json")
    try:
        with open(pkg_path, encoding="utf-8") as fh:
            pkg = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(pkg, dict):
        return None

    scripts = pkg.get("scripts") or {}
    if not isinstance(scripts, dict):
        scripts = {}
    deps = {}
    for section in ("dependencies", "devDependencies"):
        d = pkg.get(section)
        if isinstance(d, dict):
            deps.update(d)

    pm = _detect_package_manager_node(dir_path, pkg)
    has_ts = ("typescript" in deps) or os.path.exists(os.path.join(dir_path, "tsconfig.json"))
    language = "typescript" if has_ts else "javascript"

    def cmd_for(script: str) -> str | None:
        return f"{pm} run {script}" if script in scripts else None

    return {
        "path": rel_path,
        "language": language,
        "framework": _detect_framework_node(deps),
        "package_manager": pm,
        "commands": {
            "test": cmd_for("test"),
            "lint": cmd_for("lint"),
            "build": cmd_for("build"),
        },
    }


# ── Python (pyproject.toml / requirements.txt) ───────────────────────────────


def _collect_python_deps_text(text: str) -> str:
    """의존성/설정 감지용 소문자 텍스트(정식 파싱 실패 시 폴백에도 사용)."""
    return text.lower()


def _detect_framework_python(blob: str) -> str | None:
    candidates = [
        ("fastapi", "fastapi"),
        ("django", "django"),
        ("flask", "flask"),
        ("starlette", "starlette"),
    ]
    for key, name in candidates:
        if re.search(rf"(^|[^a-z0-9_]){re.escape(key)}([^a-z0-9_]|$)", blob):
            return name
    return None


def _profile_pyproject(rel_path: str, dir_path: str) -> dict[str, Any]:
    path = os.path.join(dir_path, "pyproject.toml")
    text = _read_text(path)
    lower = _collect_python_deps_text(text)
    data = _load_toml(path)

    # 패키지 매니저: uv > poetry > pip
    has_uv = ("uv" in (data.get("tool") or {})) or os.path.exists(
        os.path.join(dir_path, "uv.lock")
    ) or "[tool.uv" in lower
    has_poetry = ("poetry" in (data.get("tool") or {})) or "[tool.poetry" in lower
    if has_uv:
        pm, runner = "uv", "uv run "
    elif has_poetry:
        pm, runner = "poetry", "poetry run "
    else:
        pm, runner = "pip", ""

    tool = data.get("tool") if isinstance(data.get("tool"), dict) else {}
    has_pytest = ("pytest" in tool) or "[tool.pytest" in lower or "pytest" in lower
    has_ruff = ("ruff" in tool) or "[tool.ruff" in lower or "ruff" in lower

    test_cmd = f"{runner}pytest" if has_pytest else None
    if has_pytest and pm == "pip":
        test_cmd = "python -m pytest"
    lint_cmd = f"{runner}ruff check ." if has_ruff else None

    return {
        "path": rel_path,
        "language": "python",
        "framework": _detect_framework_python(lower),
        "package_manager": pm,
        "commands": {"test": test_cmd, "lint": lint_cmd, "build": None},
    }


def _profile_requirements(rel_path: str, dir_path: str) -> dict[str, Any]:
    text = _read_text(os.path.join(dir_path, "requirements.txt")).lower()
    has_pytest = "pytest" in text
    has_ruff = "ruff" in text
    return {
        "path": rel_path,
        "language": "python",
        "framework": _detect_framework_python(text),
        "package_manager": "pip",
        "commands": {
            "test": "python -m pytest" if has_pytest else None,
            "lint": "ruff check ." if has_ruff else None,
            "build": None,
        },
    }


# ── Go / Rust / Docker ───────────────────────────────────────────────────────


def _profile_go(rel_path: str, dir_path: str) -> dict[str, Any]:
    return {
        "path": rel_path,
        "language": "go",
        "framework": None,
        "package_manager": "go",
        "commands": {
            "test": "go test ./...",
            "lint": None,
            "build": "go build ./...",
        },
    }


def _profile_rust(rel_path: str, dir_path: str) -> dict[str, Any]:
    return {
        "path": rel_path,
        "language": "rust",
        "framework": None,
        "package_manager": "cargo",
        "commands": {
            "test": "cargo test",
            "lint": None,
            "build": "cargo build",
        },
    }


def _profile_docker(rel_path: str, dir_path: str) -> dict[str, Any]:
    return {
        "path": rel_path,
        "language": "docker-compose",
        "framework": None,
        "package_manager": "docker compose",
        "commands": {"test": None, "lint": None, "build": None},
    }


# ── 디렉터리 스캔 ─────────────────────────────────────────────────────────────


def _has_docker_compose(dir_path: str) -> bool:
    try:
        for name in os.listdir(dir_path):
            if re.fullmatch(r"docker-compose.*\.ya?ml", name):
                return True
    except OSError:
        pass
    return False


def _profile_dir(rel_path: str, dir_path: str) -> list[dict[str, Any]]:
    """한 디렉터리에서 감지되는 모든 스택 엔트리(언어별 독립 + docker)."""
    stacks: list[dict[str, Any]] = []

    if os.path.exists(os.path.join(dir_path, "package.json")):
        node = _profile_node(rel_path, dir_path)
        if node:
            stacks.append(node)

    # Python: pyproject 우선, 없을 때만 requirements(중복 방지)
    if os.path.exists(os.path.join(dir_path, "pyproject.toml")):
        stacks.append(_profile_pyproject(rel_path, dir_path))
    elif os.path.exists(os.path.join(dir_path, "requirements.txt")):
        stacks.append(_profile_requirements(rel_path, dir_path))

    if os.path.exists(os.path.join(dir_path, "go.mod")):
        stacks.append(_profile_go(rel_path, dir_path))

    if os.path.exists(os.path.join(dir_path, "Cargo.toml")):
        stacks.append(_profile_rust(rel_path, dir_path))

    if _has_docker_compose(dir_path):
        stacks.append(_profile_docker(rel_path, dir_path))

    return stacks


def scan_repo(repo: str) -> list[dict[str, Any]]:
    repo = os.path.abspath(repo)
    stacks: list[dict[str, Any]] = []

    # 루트 먼저
    stacks.extend(_profile_dir(".", repo))

    # 1-depth 하위 디렉터리(알파벳 정렬 — 결정론)
    try:
        entries = sorted(
            e for e in os.listdir(repo)
            if os.path.isdir(os.path.join(repo, e)) and not e.startswith(".")
        )
    except OSError:
        entries = []
    for entry in entries:
        stacks.extend(_profile_dir(entry, os.path.join(repo, entry)))

    return stacks


# ── 렌더러 ────────────────────────────────────────────────────────────────────


def build_profile(repo: str, stacks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": PROFILE_VERSION,
        "generated_from": os.path.abspath(repo),
        "stacks": stacks,
    }


def _cell(value: str | None) -> str:
    return f"`{value}`" if value else "—"


def render_stack_md(profile: dict[str, Any]) -> str:
    lines = [
        "# 스택 규약 프래그먼트 (Harness Tier 1 — 자동 생성)",
        "",
        "이 문서는 `stack_profiler.py`가 대상 레포를 스캔해 결정론적으로 생성한다.",
        "구현·검증 시 아래 스택별 명령을 사용하라. `—`는 감지되지 않은 명령이다.",
        "",
        "| 경로 | 언어 | 프레임워크 | 패키지매니저 | test | lint | build |",
        "|------|------|-----------|-------------|------|------|-------|",
    ]
    for s in profile["stacks"]:
        c = s.get("commands") or {}
        lines.append(
            f"| `{s['path']}` | {s.get('language') or '—'} "
            f"| {s.get('framework') or '—'} | {s.get('package_manager') or '—'} "
            f"| {_cell(c.get('test'))} | {_cell(c.get('lint'))} | {_cell(c.get('build'))} |"
        )
    if not profile["stacks"]:
        lines.append("| (감지된 스택 없음) | — | — | — | — | — | — |")
    lines.append("")
    return "\n".join(lines)


def render_gates(profile: dict[str, Any]) -> str:
    """delivery_verifier 의 VERIFY_GATES_FILE 형식 — 줄당 1명령, # 주석 허용.

    감지된 test/lint 명령을 게이트 후보로 기록한다. 게이트는 레포 루트(workdir)에서
    실행되므로, 하위 스택 명령은 `cd <path> && <cmd>` 로 감싼다.
    """
    lines = [
        "# 자동 생성 게이트 후보 (stack_profiler.py) — VERIFY_GATES_FILE 형식",
        "# 줄당 1명령. 전부 exit 0 이어야 검증 통과. 불필요한 게이트는 주석(#) 처리.",
    ]
    seen: set[str] = set()
    for s in profile["stacks"]:
        c = s.get("commands") or {}
        for key in ("lint", "test"):
            cmd = c.get(key)
            if not cmd:
                continue
            full = cmd if s["path"] == "." else f"cd {s['path']} && {cmd}"
            if full in seen:
                continue
            seen.add(full)
            lines.append(full)
    if len(seen) == 0:
        lines.append("# (감지된 test/lint 명령 없음 — 게이트 후보 비어 있음)")
    return "\n".join(lines) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="스택 프로파일러 (Harness Tier 1)")
    p.add_argument("--repo", required=True, help="스캔 대상 레포 경로")
    p.add_argument("--out", default=None, help="산출 디렉터리(기본: <repo>/.claude)")
    p.add_argument("--gates-name", default="harness-gates.txt",
                   help="gates 파일 이름(기본: harness-gates.txt)")
    args = p.parse_args(argv)

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(repo):
        print(f"[stack_profiler] 레포 경로가 없음: {repo}", file=sys.stderr)
        return 2

    out_dir = os.path.abspath(args.out) if args.out else os.path.join(repo, ".claude")
    os.makedirs(out_dir, exist_ok=True)

    stacks = scan_repo(repo)
    profile = build_profile(repo, stacks)

    profile_path = os.path.join(out_dir, "harness-profile.json")
    with open(profile_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    stack_md_path = os.path.join(out_dir, "CLAUDE.stack.md")
    with open(stack_md_path, "w", encoding="utf-8") as fh:
        fh.write(render_stack_md(profile))

    gates_path = os.path.join(out_dir, args.gates_name)
    with open(gates_path, "w", encoding="utf-8") as fh:
        fh.write(render_gates(profile))

    print(json.dumps({
        "profile": profile_path,
        "stack_md": stack_md_path,
        "gates": gates_path,
        "stack_count": len(stacks),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
