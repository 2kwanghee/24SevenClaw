#!/usr/bin/env python3
"""workspace_provision.sh 조달 스크립트 통합 테스트 (CE-344 settings.json 보존 정책).

검증 축:
  1. 신규 조달 — 대상 레포에 기존 .claude/settings.json 없음 → 코어 settings.json
     그대로 복사(현행과 동일, 바이트 수준). settings.core.json 은 생성되지 않는다.
  2. 보존 케이스 — 대상 레포에 기존 .claude/settings.json 있음 → 원본 보존(바이트
     수준) + 코어 버전은 settings.core.json 으로 병치 + 경고 로그 출력.
  3. 멱등 — 신규 조달 시나리오를 동일 --key/--dest 로 2회 연속 실행해도
     .claude/settings.json 내용이 바이트 단위로 동일하게 유지된다.

bash 스크립트이므로 subprocess.run 으로 scripts/workspace_provision.sh 를 실행해
결과 파일(.claude/settings.json, .claude/settings.core.json)을 검증한다.
clone 소스는 tmp_path 아래 로컬 git fixture repo 를 사용(레포 실제 workspaces/
디렉터리는 --dest 로 tmp_path 하위를 지정해 건드리지 않는다).

Usage:
    cd ClickEye && pytest scripts/tests/test_workspace_provision.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SCRIPT = os.path.join(_REPO_ROOT, "scripts", "workspace_provision.sh")
_CORE_SETTINGS = os.path.join(_REPO_ROOT, "templates", "harness-core", "settings.json")


def _git(args, cwd, check=True):
    return subprocess.run(
        ["git", "-c", "commit.gpgsign=false"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
        env={**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
             "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"},
    )


def _make_source_repo(tmp_path, name="source_repo", custom_settings=None):
    """clone 가능한 로컬 fixture git repo 를 만든다.

    custom_settings 가 주어지면 .claude/settings.json 을 그 내용으로 커밋해
    "대상 레포에 이미 settings.json 이 있는" 시나리오를 재현한다.
    """
    src = tmp_path / name
    src.mkdir()
    _git(["init"], cwd=src)
    _git(["config", "user.email", "test@example.com"], cwd=src)
    _git(["config", "user.name", "Test"], cwd=src)
    (src / "README.md").write_text("workspace_provision 테스트용 fixture repo\n", encoding="utf-8")
    if custom_settings is not None:
        claude_dir = src / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        (claude_dir / "settings.json").write_text(
            json.dumps(custom_settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    _git(["add", "-A"], cwd=src)
    _git(["commit", "-m", "init"], cwd=src)
    return src


def _run_provision(key, source, dest):
    result = subprocess.run(
        ["bash", _SCRIPT, "--key", key, "--source", str(source), "--dest", str(dest)],
        capture_output=True,
        text=True,
    )
    return result


def _assert_ok(result):
    assert result.returncode == 0, (
        f"workspace_provision.sh 실패 (rc={result.returncode})\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


# ── ① 신규 조달 (기존 settings.json 없음) — 현행과 동일 결과 ─────────────────────


def test_fresh_provision_copies_core_settings(tmp_path):
    src = _make_source_repo(tmp_path, name="source_fresh")
    dest = tmp_path / "dest_fresh"

    result = _run_provision("test-fresh", src, dest)
    _assert_ok(result)

    ws_settings = dest / "test-fresh" / ".claude" / "settings.json"
    ws_settings_core = dest / "test-fresh" / ".claude" / "settings.core.json"

    assert ws_settings.exists(), f".claude/settings.json 이 생성되지 않음\nstdout:\n{result.stdout}"
    assert ws_settings.read_bytes() == open(_CORE_SETTINGS, "rb").read(), (
        "신규 조달 시 settings.json 은 코어 템플릿과 바이트 동일해야 함"
    )
    assert not ws_settings_core.exists(), (
        "신규 조달(기존 settings.json 없음)에서는 settings.core.json 이 생성되면 안 됨"
    )


# ── ② 보존 케이스 (기존 settings.json 있음) ──────────────────────────────────────


def test_existing_settings_preserved_with_core_sidecar(tmp_path):
    custom = {"custom": "customer-hook"}
    src = _make_source_repo(tmp_path, name="source_custom", custom_settings=custom)
    dest = tmp_path / "dest_custom"

    result = _run_provision("test-custom", src, dest)
    _assert_ok(result)

    ws_settings = dest / "test-custom" / ".claude" / "settings.json"
    ws_settings_core = dest / "test-custom" / ".claude" / "settings.core.json"

    expected_custom_bytes = json.dumps(custom, ensure_ascii=False, indent=2).encode("utf-8")
    assert ws_settings.read_bytes() == expected_custom_bytes, (
        "기존 settings.json 이 있으면 원본을 그대로 보존해야 함(덮어쓰기 금지)"
    )
    assert ws_settings_core.exists(), "보존 케이스에서는 settings.core.json 이 코어 버전으로 병치되어야 함"
    assert ws_settings_core.read_bytes() == open(_CORE_SETTINGS, "rb").read(), (
        "settings.core.json 은 코어 템플릿과 바이트 동일해야 함"
    )

    combined_output = result.stdout + result.stderr
    assert "settings.core.json" in combined_output, (
        f"보존 시 settings.core.json 관련 경고 로그가 출력되어야 함\n출력:\n{combined_output}"
    )


# ── ③ 멱등 — 동일 --key/--dest 2회 연속 실행 ──────────────────────────────────


def test_idempotent_repeated_provision(tmp_path):
    src = _make_source_repo(tmp_path, name="source_idem")
    dest = tmp_path / "dest_idem"

    first = _run_provision("test-idem", src, dest)
    _assert_ok(first)
    ws_settings = dest / "test-idem" / ".claude" / "settings.json"
    first_bytes = ws_settings.read_bytes()

    second = _run_provision("test-idem", src, dest)
    _assert_ok(second)
    second_bytes = ws_settings.read_bytes()

    assert first_bytes == second_bytes, "동일 --key/--dest 2회 실행 시 settings.json 내용이 바이트 동일해야 함"

    ws_settings_core = dest / "test-idem" / ".claude" / "settings.core.json"
    if ws_settings_core.exists():
        # 2회차부터는 settings.json 이 이미 존재하는 파일로 간주되어 보존 분기를 타면서
        # settings.core.json 이 병치될 수 있다(정책상 정상 — 스크립트는 파일 내용을
        # 검사하지 않고 존재 여부만으로 판단). 병치된다면 코어 템플릿과 바이트 동일해야 함.
        assert ws_settings_core.read_bytes() == open(_CORE_SETTINGS, "rb").read()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
