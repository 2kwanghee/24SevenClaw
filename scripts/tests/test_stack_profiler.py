#!/usr/bin/env python3
"""stack_profiler 단위 테스트 — Python/Node/모노레포 픽스처 + 감지 실패 시 null 유지."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stack_profiler  # noqa: E402


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _stack_for(profile: dict, path: str, language: str) -> dict:
    for s in profile["stacks"]:
        if s["path"] == path and s["language"] == language:
            return s
    raise AssertionError(f"스택 없음: path={path} language={language} — {profile['stacks']}")


# ── ① Python (pyproject + pytest + ruff, uv) ─────────────────────────────────


def test_python_pyproject(tmp_path):
    repo = str(tmp_path)
    _write(os.path.join(repo, "pyproject.toml"), """
[project]
name = "demo"
dependencies = ["fastapi"]

[tool.uv]
dev-dependencies = ["pytest", "ruff"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
""")
    stacks = stack_profiler.scan_repo(repo)
    profile = stack_profiler.build_profile(repo, stacks)
    s = _stack_for(profile, ".", "python")
    assert s["package_manager"] == "uv"
    assert s["framework"] == "fastapi"
    assert s["commands"]["test"] == "uv run pytest"
    assert s["commands"]["lint"] == "uv run ruff check ."
    assert s["commands"]["build"] is None


# ── ② Node (package.json scripts) ────────────────────────────────────────────


def test_node_package_json(tmp_path):
    repo = str(tmp_path)
    _write(os.path.join(repo, "package.json"), json.dumps({
        "name": "web",
        "packageManager": "pnpm@9.0.0",
        "scripts": {"test": "vitest", "lint": "eslint .", "build": "next build"},
        "dependencies": {"next": "15.0.0", "react": "18.0.0"},
        "devDependencies": {"typescript": "5.0.0"},
    }))
    stacks = stack_profiler.scan_repo(repo)
    profile = stack_profiler.build_profile(repo, stacks)
    s = _stack_for(profile, ".", "typescript")
    assert s["package_manager"] == "pnpm"
    assert s["framework"] == "next"
    assert s["commands"]["test"] == "pnpm run test"
    assert s["commands"]["lint"] == "pnpm run lint"
    assert s["commands"]["build"] == "pnpm run build"


# ── ③ 모노레포 (하위에 Python + Node 동시) ───────────────────────────────────


def test_monorepo(tmp_path):
    repo = str(tmp_path)
    _write(os.path.join(repo, "api", "pyproject.toml"), """
[project]
name = "api"
dependencies = ["django"]

[tool.poetry]
name = "api"

[tool.pytest.ini_options]
testpaths = ["tests"]
""")
    _write(os.path.join(repo, "web", "package.json"), json.dumps({
        "name": "web",
        "scripts": {"test": "jest", "build": "vite build"},
        "dependencies": {"vue": "3.0.0"},
    }))
    _write(os.path.join(repo, "web", "package-lock.json"), "{}")
    stacks = stack_profiler.scan_repo(repo)
    profile = stack_profiler.build_profile(repo, stacks)

    api = _stack_for(profile, "api", "python")
    assert api["package_manager"] == "poetry"
    assert api["framework"] == "django"
    assert api["commands"]["test"] == "poetry run pytest"
    # ruff 미감지 → null 유지(추측 금지)
    assert api["commands"]["lint"] is None

    web = _stack_for(profile, "web", "javascript")
    assert web["package_manager"] == "npm"
    assert web["framework"] == "vue"
    assert web["commands"]["test"] == "npm run test"
    # lint 스크립트 부재 → null 유지
    assert web["commands"]["lint"] is None
    assert web["commands"]["build"] == "npm run build"

    # gates 파일: 하위 스택은 cd 로 감싼다
    gates = stack_profiler.render_gates(profile)
    assert "cd api && poetry run pytest" in gates
    assert "cd web && npm run test" in gates


# ── ④ 감지 실패 시 null 유지 (빈 pyproject) ──────────────────────────────────


def test_no_commands_detected(tmp_path):
    repo = str(tmp_path)
    _write(os.path.join(repo, "pyproject.toml"), """
[project]
name = "bare"
version = "0.1.0"
""")
    stacks = stack_profiler.scan_repo(repo)
    profile = stack_profiler.build_profile(repo, stacks)
    s = _stack_for(profile, ".", "python")
    # pytest/ruff 증거 없음 → 전부 null
    assert s["commands"]["test"] is None
    assert s["commands"]["lint"] is None
    assert s["commands"]["build"] is None
    # 게이트 후보 비어 있음(위장 금지)
    gates = stack_profiler.render_gates(profile)
    assert "감지된 test/lint 명령 없음" in gates


# ── ⑤ CLI 산출 3종 파일 생성 ─────────────────────────────────────────────────


def test_cli_outputs(tmp_path):
    repo = tmp_path / "repo"
    out = tmp_path / "out"
    _write(str(repo / "package.json"), json.dumps({
        "scripts": {"test": "jest"}, "dependencies": {"react": "18"},
    }))
    rc = stack_profiler.main(["--repo", str(repo), "--out", str(out)])
    assert rc == 0
    assert (out / "harness-profile.json").exists()
    assert (out / "CLAUDE.stack.md").exists()
    assert (out / "harness-gates.txt").exists()
    prof = json.loads((out / "harness-profile.json").read_text(encoding="utf-8"))
    assert prof["version"] == 1
    assert prof["stacks"][0]["commands"]["test"] == "npm run test"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
