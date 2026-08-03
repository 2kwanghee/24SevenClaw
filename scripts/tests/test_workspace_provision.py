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


def _run_provision(key, source, dest, enforcement=None):
    """조달 실행. enforcement=None 이면 FLOWOPS_ENFORCEMENT 를 env 에서 제거해
    토글 off(현행) 경로를 결정적으로 재현한다(CE-329).
    """
    env = {k: v for k, v in os.environ.items() if k != "FLOWOPS_ENFORCEMENT"}
    if enforcement is not None:
        env["FLOWOPS_ENFORCEMENT"] = enforcement
    result = subprocess.run(
        ["bash", _SCRIPT, "--key", key, "--source", str(source), "--dest", str(dest)],
        capture_output=True,
        text=True,
        env=env,
    )
    return result


def _pre_tool_use(settings_path):
    with open(settings_path, encoding="utf-8") as fp:
        return json.load(fp).get("hooks", {}).get("PreToolUse", [])


_ENFORCE_BUNDLE = "gitguard-gate.cjs"


def _enforce_entries(settings_path):
    """집행면 훅 명령을 담은 PreToolUse 엔트리만 골라낸다.

    명령 문자열은 fail-closed 보강(F8: 경로 폴백 + `|| exit 2`)으로 바뀔 수 있으므로
    배선 판정과 동일하게 **번들 파일명** 기준으로 찾는다(훅 1개 = 번들 1개).
    """
    return [
        e
        for e in _pre_tool_use(settings_path)
        if any(_ENFORCE_BUNDLE in str(h.get("command", "")) for h in e.get("hooks", []))
    ]


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


# ── ④ P8 집행면 게이트 배선 (CE-329, 이중 opt-in) ──────────────────────────────


def test_enforcement_off_output_unchanged(tmp_path):
    """토글 off(미설정) — settings.json 은 코어 템플릿과 바이트 동일, 번들 미복사."""
    src = _make_source_repo(tmp_path, name="source_enf_off")
    dest = tmp_path / "dest_enf_off"

    result = _run_provision("test-enf-off", src, dest)
    _assert_ok(result)

    claude = dest / "test-enf-off" / ".claude"
    assert (claude / "settings.json").read_bytes() == open(_CORE_SETTINGS, "rb").read(), (
        "토글 off 에서는 settings 산출물이 현행(코어 템플릿)과 바이트 동일해야 함"
    )
    assert not (claude / "hooks" / "gitguard-gate.cjs").exists(), (
        "토글 off 에서는 집행면 번들이 물질화되면 안 됨"
    )
    # 짝 목록(.harness/)은 토글과 무관하게 등재된다 — 없는 디렉터리 exclude 는 no-op 이고,
    # auto_dev_pipeline.sh 의 ws_exclude_harness_artifacts 와 조건이 갈리면 불변식이 깨진다.
    exclude = (dest / "test-enf-off" / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".harness/" in exclude.split("\n"), (
        f"clone-로컬 제외 짝 목록에 .harness/ 가 없음\nexclude:\n{exclude}"
    )


def test_enforcement_on_fresh_provision_wires_hook(tmp_path):
    """토글 on + 신규 조달 — 번들 복사 + PreToolUse 엔트리 1개 가산."""
    src = _make_source_repo(tmp_path, name="source_enf_fresh")
    dest = tmp_path / "dest_enf_fresh"

    result = _run_provision("test-enf-fresh", src, dest, enforcement="true")
    _assert_ok(result)

    claude = dest / "test-enf-fresh" / ".claude"
    bundle = claude / "hooks" / "gitguard-gate.cjs"
    assert bundle.exists(), f"집행면 번들이 복사되지 않음\nstdout:\n{result.stdout}"
    assert bundle.read_bytes() == open(
        os.path.join(_REPO_ROOT, "templates", "harness-core", "hooks", "gitguard-gate.cjs"), "rb"
    ).read(), "복사된 번들은 코어 산출물과 바이트 동일해야 함"

    entries = _enforce_entries(claude / "settings.json")
    assert len(entries) == 1, f"집행면 PreToolUse 엔트리가 정확히 1개여야 함: {entries}"
    assert entries[0]["matcher"] == "Bash|Write|Edit|MultiEdit|NotebookEdit"
    assert entries[0]["hooks"][0]["timeout"] == 15

    # 감사 로그가 고객 clone 을 상시 "더러운 트리" 로 만들지 않아야 한다(CE-347 stash 상시화 방지)
    exclude = (dest / "test-enf-fresh" / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert ".harness/" in exclude.split("\n"), (
        f"토글 on 조달은 .harness/ 를 clone-로컬 제외에 넣어야 함\nexclude:\n{exclude}"
    )

    # 코어의 기존 plan-gate 엔트리는 그대로 남아야 한다(가산 병합, 대체 아님).
    commands = [
        h.get("command") for e in _pre_tool_use(claude / "settings.json") for h in e.get("hooks", [])
    ]
    assert any("harness-plan-gate.sh" in (c or "") for c in commands), (
        "기존 코어 훅이 사라졌음 — 가산 병합이 아니라 대체가 일어났다"
    )


def test_enforcement_on_preserved_settings_merge(tmp_path):
    """토글 on + CE-344 보존 경로 — 고객 settings 에 엔트리만 가산, 타 키 불변, 2회 멱등."""
    custom = {
        "permissions": {"allow": ["Bash(customer-tool *)"]},
        "env": {"CUSTOMER_FLAG": "1"},
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write",
                    "hooks": [{"type": "command", "command": "bash customer-hook.sh"}],
                }
            ]
        },
    }
    src = _make_source_repo(tmp_path, name="source_enf_keep", custom_settings=custom)
    dest = tmp_path / "dest_enf_keep"

    first = _run_provision("test-enf-keep", src, dest, enforcement="true")
    _assert_ok(first)

    settings = dest / "test-enf-keep" / ".claude" / "settings.json"
    with open(settings, encoding="utf-8") as fp:
        merged = json.load(fp)

    # 다른 키 불변
    assert merged["permissions"] == custom["permissions"], "고객 permissions 가 변경됨"
    assert merged["env"] == custom["env"], "고객 env 가 변경됨"
    # 고객 훅 보존 + 집행면 엔트리 가산
    assert merged["hooks"]["PreToolUse"][0] == custom["hooks"]["PreToolUse"][0], (
        "고객 PreToolUse 엔트리가 보존되지 않음"
    )
    assert len(_enforce_entries(settings)) == 1
    assert len(merged["hooks"]["PreToolUse"]) == 2, "엔트리는 고객 1 + 집행면 1 이어야 함"

    # 2회 실행 멱등 — 바이트 동일
    first_bytes = settings.read_bytes()
    second = _run_provision("test-enf-keep", src, dest, enforcement="true")
    _assert_ok(second)
    assert settings.read_bytes() == first_bytes, "2회 조달 시 settings.json 이 바이트 동일해야 함(멱등)"
    assert len(_enforce_entries(settings)) == 1, "재실행에서 엔트리가 중복 추가됨"
    assert "멱등" in (second.stdout + second.stderr), "멱등 경로 로그가 보이지 않음"


def test_enforcement_idempotent_by_bundle_filename(tmp_path):
    """표기가 다른 기존 엔트리도 중복 추가하지 않는다(CE-329 E5).

    정확 문자열 일치로 판정하면 경로 표기·따옴표가 바뀔 때 같은 훅이 누적된다.
    """
    custom = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    # 같은 번들인데 표기가 다르다(따옴표 없음 + 상대경로)
                    "hooks": [{"type": "command", "command": "node .claude/hooks/gitguard-gate.cjs"}],
                }
            ]
        }
    }
    src = _make_source_repo(tmp_path, name="source_enf_dup", custom_settings=custom)
    dest = tmp_path / "dest_enf_dup"

    result = _run_provision("test-enf-dup", src, dest, enforcement="true")
    _assert_ok(result)

    settings = dest / "test-enf-dup" / ".claude" / "settings.json"
    bundle_refs = [
        h
        for e in _pre_tool_use(settings)
        for h in e.get("hooks", [])
        if "gitguard-gate.cjs" in str(h.get("command", ""))
    ]
    assert len(bundle_refs) == 1, f"표기가 다른 동일 훅이 중복 추가됨: {bundle_refs}"
    assert "멱등" in (result.stdout + result.stderr)


def _fake_repo_root(tmp_path, env_text, name="fakerepo"):
    """`.env` 를 통제할 수 있는 가짜 레포 루트 (CE-329 F3).

    실제 스크립트·템플릿은 심볼릭으로 붙인다. `workspace_provision.sh` 와
    `pipeline_config.sh` 는 각자 BASH_SOURCE 기준으로 PROJECT_DIR 을 잡으므로,
    이 루트에서 실행하면 여기 `.env` 를 읽는다 — 레포 실제 `.env` 에 의존하지 않는다.
    """
    root = tmp_path / name
    (root / "scripts").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    for fname in ("workspace_provision.sh", "pipeline_config.sh", "stack_profiler.py"):
        os.symlink(os.path.join(_REPO_ROOT, "scripts", fname), root / "scripts" / fname)
    os.symlink(
        os.path.join(_REPO_ROOT, "templates", "harness-core"), root / "templates" / "harness-core"
    )
    (root / ".env").write_text(env_text, encoding="utf-8")
    return root


def _run_from_root(root, key, source, dest, enforcement=None):
    env = {k: v for k, v in os.environ.items() if k != "FLOWOPS_ENFORCEMENT"}
    if enforcement is not None:
        env["FLOWOPS_ENFORCEMENT"] = enforcement
    return subprocess.run(
        [
            "bash",
            str(root / "scripts" / "workspace_provision.sh"),
            "--key", key, "--source", str(source), "--dest", str(dest),
        ],
        capture_output=True,
        text=True,
        env=env,
    )


def test_caller_env_beats_dotenv_toggle(tmp_path):
    """호출자 env 가 `.env` 를 이긴다 — 조용한 미배선 방지 (CE-329 F3).

    `pipeline_config.sh` 의 기본 동작은 `.env` 로 이미 set 된 값을 덮는 것이라,
    보정이 없으면 `FLOWOPS_ENFORCEMENT=true` 로 호출해도 `.env` 의 false 에 강등돼
    게이트가 조용히 빠진다(CE-345/346 오귀속 계열의 재발).
    """
    root = _fake_repo_root(tmp_path, "FLOWOPS_ENFORCEMENT=false\n", name="root_override")
    src = _make_source_repo(tmp_path, name="source_f3a")
    dest = tmp_path / "dest_f3a"

    result = _run_from_root(root, "f3a", src, dest, enforcement="true")
    _assert_ok(result)
    settings = dest / "f3a" / ".claude" / "settings.json"
    assert len(_enforce_entries(settings)) == 1, (
        f".env=false 가 호출자 env=true 를 덮어 미배선됨\nstdout:\n{result.stdout}"
    )


def test_dotenv_toggle_still_applies_when_caller_silent(tmp_path):
    """호출자가 말이 없으면 `.env` 설정이 그대로 적용된다(보정이 .env 를 무력화하지 않음)."""
    root_on = _fake_repo_root(tmp_path, "FLOWOPS_ENFORCEMENT=true\n", name="root_on")
    src = _make_source_repo(tmp_path, name="source_f3b")
    dest_on = tmp_path / "dest_f3b_on"
    result_on = _run_from_root(root_on, "f3b", src, dest_on)
    _assert_ok(result_on)
    assert len(_enforce_entries(dest_on / "f3b" / ".claude" / "settings.json")) == 1, (
        ".env=true 인데 배선되지 않음"
    )

    root_off = _fake_repo_root(tmp_path, "FLOWOPS_ENFORCEMENT=false\n", name="root_off")
    dest_off = tmp_path / "dest_f3b_off"
    result_off = _run_from_root(root_off, "f3c", src, dest_off)
    _assert_ok(result_off)
    assert _enforce_entries(dest_off / "f3c" / ".claude" / "settings.json") == [], (
        ".env=false 인데 배선됨"
    )


def test_hook_command_is_fail_closed(tmp_path):
    """훅 명령이 두 fail-open 경로를 닫는다 (CE-329 F8).

    ① CLAUDE_PROJECT_DIR 미설정 → `node /.claude/...` 로 rc=1(자문형)
    ② 번들 삭제/손상 → node 가 rc=1
    둘 다 "게이트가 조용히 열리는" 경로다.
    """
    src = _make_source_repo(tmp_path, name="source_f8")
    dest = tmp_path / "dest_f8"
    _assert_ok(_run_provision("f8", src, dest, enforcement="true"))

    ws = dest / "f8"
    entry = _enforce_entries(ws / ".claude" / "settings.json")[0]
    command = entry["hooks"][0]["command"]
    assert "${CLAUDE_PROJECT_DIR:-" in command, f"경로 폴백이 없음: {command}"
    assert command.rstrip().endswith("|| exit 2"), f"rc=1 → 2 전환이 없음: {command}"

    payload = json.dumps(
        {"cwd": str(ws), "tool_name": "Bash", "tool_input": {"command": "git add -A"}}
    )
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}

    def _run_hook():
        return subprocess.run(
            ["sh", "-c", command], input=payload, capture_output=True, text=True,
            cwd=str(ws), env=env,
        ).returncode

    assert _run_hook() == 2, "CLAUDE_PROJECT_DIR 미설정에서 차단되지 않음"
    (ws / ".claude" / "hooks" / "gitguard-gate.cjs").unlink()
    assert _run_hook() == 2, "번들이 없을 때 rc=1(자문형)로 새어나감 — fail-open"


def test_exclude_pair_invariant_with_pipeline(tmp_path):
    """clone-로컬 제외 목록이 auto_dev_pipeline.sh 의 자기치유 목록과 짝을 이룬다(CE-329 E3).

    한쪽만 바뀌면 provision 미경유 워크스페이스(기존 조달분)의 자기치유가 비어
    `.harness/` 감사 로그가 매 런 "더러운 트리" 판정을 참으로 만든다.
    """
    provision = open(_SCRIPT, encoding="utf-8").read()
    pipeline = open(
        os.path.join(_REPO_ROOT, "scripts", "auto_dev_pipeline.sh"), encoding="utf-8"
    ).read()

    entries = ["'.clickeye_default_branch'", "'.claude/'", "'CLAUDE.md'", "'.harness/'"]
    for e in entries:
        assert e in provision, f"workspace_provision.sh 제외 목록에 {e} 없음"
        assert e in pipeline, f"auto_dev_pipeline.sh ws_exclude_harness_artifacts 에 {e} 없음"


def test_enforcement_on_broken_customer_settings_is_non_blocking(tmp_path):
    """고객 settings.json 이 손상된 JSON — 경고만 남기고 조달은 성공해야 한다(비차단)."""
    src = _make_source_repo(tmp_path, name="source_enf_broken")
    # custom_settings 는 dict 만 받으므로 손상 JSON 은 커밋 후 직접 덮어쓴다.
    claude_dir = src / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text("{ 이건 JSON 이 아니다", encoding="utf-8")
    _git(["add", "-A"], cwd=src)
    _git(["commit", "-m", "broken settings"], cwd=src)

    dest = tmp_path / "dest_enf_broken"
    result = _run_provision("test-enf-broken", src, dest, enforcement="true")
    _assert_ok(result)  # 조달 자체는 성공

    combined = result.stdout + result.stderr
    assert "집행면 훅 병합 실패" in combined, f"병합 실패 경고가 없음\n출력:\n{combined}"
    # fail-open 이 조용하면 게이트가 없는 워크스페이스를 있는 줄 알고 쓴다(CE-329 E4)
    assert "미배선" in combined and "게이트 없음" in combined, (
        f"병합 실패 시 '집행면 미배선(게이트 없음)' 사실이 로그에 드러나야 함\n출력:\n{combined}"
    )
    settings = dest / "test-enf-broken" / ".claude" / "settings.json"
    assert settings.read_text(encoding="utf-8") == "{ 이건 JSON 이 아니다", (
        "병합 실패 시 고객 settings.json 은 원본 그대로여야 함"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
