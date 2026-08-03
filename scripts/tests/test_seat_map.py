#!/usr/bin/env python3
"""seat_map 단위 테스트 (다프로젝트화 P5/CE-345).

검증 축:
  1. 등재→배정→해석 정상 경로 — resolve 가 SEAT_ID + SEAT_TOKEN_FILE 를 낸다.
  2. 멱등 — 동일 등재/배정 2회 = 파일 바이트 동일(updated_at 유지).
  3. 해석 빈 출력 — 미배정 / pending_login / disabled / 토큰 파일 부재(전부 exit 0).
  4. 1시트:1워크스페이스 가드 — --force 없이 재배정 거부 + 원장 무변경.
  5. 비밀 위생 — resolve 출력에 토큰 **값**이 없다(경로만).
  6. workspaces.json 미접근 — 매핑 원장이 없어도 전 서브커맨드가 동작한다.

네트워크 호출 없음(전 서브커맨드 오프라인).

Usage:
    cd ClickEye && pytest scripts/tests/test_seat_map.py -v
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seat_map as sm  # noqa: E402

TOKEN_VALUE = "sk-ant-oat01-테스트토큰값-절대노출금지"


# ── 헬퍼: 레포 모양(<repo>/.ralph/seats.json + <repo>/.ralph/seats/<id>.token) 구성 ──


def _make_repo(tmp_path, token_name: str = "seat-a.token") -> tuple[str, str]:
    """원장 경로와 **원장 상대** 토큰 경로를 만든다. 토큰 파일은 실제로 생성한다."""
    ralph = tmp_path / ".ralph"
    (ralph / "seats").mkdir(parents=True)
    token = ralph / "seats" / token_name
    token.write_text(TOKEN_VALUE, encoding="utf-8")
    return str(ralph / "seats.json"), f".ralph/seats/{token_name}"


def _run(ledger_path: str, *argv: str) -> int:
    return sm.main([*argv, "--output", ledger_path])


# ── ① 등재 → 배정 → 해석 정상 경로 ────────────────────────────────────────────


def test_register_assign_resolve(tmp_path, capsys):
    out, token_rel = _make_repo(tmp_path)

    assert _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel, "--label", "계정 A") == 0
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a") == 0
    capsys.readouterr()

    assert _run(out, "resolve", "--resolve-key", "3be49b62") == 0
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    assert len(lines) == 2
    assert lines[0] == "SEAT_ID=seat-a"
    assert lines[1].startswith("SEAT_TOKEN_FILE=")
    # 상대경로는 원장 기준 절대경로로 해석된다(소비자 cwd 무관 — STEP B 는 워크스페이스로 cd 한다).
    emitted = lines[1].split("=", 1)[1]
    assert os.path.isfile(emitted)
    assert emitted.endswith(os.path.join(".ralph", "seats", "seat-a.token"))

    saved = json.loads(open(out, encoding="utf-8").read())
    assert saved["version"] == 1
    assert saved["seats"]["seat-a"]["status"] == "active"
    assert saved["seats"]["seat-a"]["label"] == "계정 A"
    assert saved["seats"]["seat-a"]["auth"] == {"oauth_token_file": token_rel}
    assert saved["assignments"] == {"3be49b62": "seat-a"}


def test_resolve_config_dir_fallback(tmp_path, capsys):
    out, _ = _make_repo(tmp_path)
    cfg = tmp_path / "seat-b-config"
    cfg.mkdir()

    assert _run(out, "register-seat", "--id", "seat-b", "--config-dir", str(cfg)) == 0
    assert _run(out, "assign", "--workspace", "77c0ffee", "--seat", "seat-b") == 0
    capsys.readouterr()

    assert _run(out, "resolve", "--resolve-key", "77c0ffee") == 0
    stdout = capsys.readouterr().out
    assert "SEAT_ID=seat-b" in stdout
    assert f"SEAT_CONFIG_DIR={cfg}" in stdout
    assert "SEAT_TOKEN_FILE" not in stdout


# ── ② 멱등 — 동일 호출 2회 = 파일 바이트 동일 ─────────────────────────────────


def test_idempotent_bytes(tmp_path, capsys):
    out, token_rel = _make_repo(tmp_path)

    assert _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel, "--label", "계정 A") == 0
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a") == 0
    first = open(out, "rb").read()

    # 같은 등재/배정을 반복해도 내용이 변하지 않으므로 updated_at 도 유지된다.
    assert _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel, "--label", "계정 A") == 0
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a") == 0
    capsys.readouterr()
    assert open(out, "rb").read() == first

    # 실제 변경(라벨)이 생기면 갱신된다 — 멱등이 "영구 동결"은 아님을 확인.
    assert _run(out, "register-seat", "--id", "seat-a", "--label", "계정 A2") == 0
    assert open(out, "rb").read() != first


def test_register_preserves_manual_values(tmp_path):
    out, token_rel = _make_repo(tmp_path)
    assert _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel, "--label", "계정 A") == 0

    ledger = json.loads(open(out, encoding="utf-8").read())
    ledger["seats"]["seat-a"]["note"] = "운영자 메모"
    sm.write_ledger(out, ledger)

    # 라벨만 갱신 — auth/note 는 인자로 덮어쓰지 않는 한 보존된다.
    assert _run(out, "register-seat", "--id", "seat-a", "--label", "계정 A 갱신") == 0
    saved = json.loads(open(out, encoding="utf-8").read())
    assert saved["seats"]["seat-a"]["note"] == "운영자 메모"
    assert saved["seats"]["seat-a"]["auth"] == {"oauth_token_file": token_rel}
    assert saved["seats"]["seat-a"]["label"] == "계정 A 갱신"


# ── ③ 해석 빈 출력 (전부 exit 0 — 기본 세션 폴백) ─────────────────────────────


def test_resolve_empty_unassigned_key(tmp_path, capsys):
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    capsys.readouterr()

    assert _run(out, "resolve", "--resolve-key", "없는키") == 0
    assert capsys.readouterr().out.strip() == ""


def test_resolve_empty_no_ledger(tmp_path, capsys):
    missing = str(tmp_path / ".ralph" / "seats.json")
    assert _run(missing, "resolve", "--resolve-key", "3be49b62") == 0
    assert capsys.readouterr().out.strip() == ""
    assert not os.path.exists(missing)  # 해석은 원장을 만들지 않는다


def test_resolve_empty_pending_login(tmp_path, capsys):
    out, _ = _make_repo(tmp_path)
    # 인증 경로가 없으면 status 는 pending_login 으로 강제된다.
    assert _run(out, "register-seat", "--id", "seat-a") == 0
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a") == 0
    capsys.readouterr()

    assert json.loads(open(out, encoding="utf-8").read())["seats"]["seat-a"]["status"] == "pending_login"
    assert _run(out, "resolve", "--resolve-key", "3be49b62") == 0
    assert capsys.readouterr().out.strip() == ""


def test_resolve_disabled_emits_blocked(tmp_path, capsys):
    """disabled 시트는 빈 출력(=조용한 기본 계정 폴백)이 아니라 차단 신호를 낸다."""
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a")
    assert _run(out, "set-status", "--seat", "seat-a", "--status", "disabled") == 0
    capsys.readouterr()

    assert _run(out, "resolve", "--resolve-key", "3be49b62") == 0
    stdout = capsys.readouterr().out
    assert stdout.strip() == "SEAT_BLOCKED=disabled"
    # 차단 신호에는 시트 식별자도 경로도 싣지 않는다(호출부는 단계를 막기만 하면 된다).
    assert "SEAT_ID" not in stdout
    assert "SEAT_TOKEN_FILE" not in stdout

    # 다시 active 로 되돌리면 해석된다(한도도달→회복 운영 시나리오).
    assert _run(out, "set-status", "--seat", "seat-a", "--status", "active") == 0
    capsys.readouterr()
    assert _run(out, "resolve", "--resolve-key", "3be49b62") == 0
    assert "SEAT_ID=seat-a" in capsys.readouterr().out


def test_resolve_empty_token_file_missing(tmp_path, capsys):
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a")
    capsys.readouterr()

    os.remove(os.path.join(str(tmp_path), token_rel))  # 토큰 파일 소실(로그아웃/정리)
    assert _run(out, "resolve", "--resolve-key", "3be49b62") == 0
    assert capsys.readouterr().out.strip() == ""


def test_resolve_empty_token_file_unreadable(tmp_path, capsys):
    """존재하지만 읽히지 않는 토큰 파일 = 시트 미확보(호출부가 시트를 참칭하면 안 된다)."""
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a")
    capsys.readouterr()

    token_path = os.path.join(str(tmp_path), token_rel)
    os.chmod(token_path, 0o000)
    if os.access(token_path, os.R_OK):  # root 등 권한 무시 환경에서는 의미 없는 검사
        pytest.skip("이 환경에서는 파일 권한이 강제되지 않는다(root?)")
    try:
        assert _run(out, "resolve", "--resolve-key", "3be49b62") == 0
        assert capsys.readouterr().out.strip() == ""
    finally:
        os.chmod(token_path, 0o600)


def test_register_status_disabled_allowed(tmp_path):
    """CLI choices 가 API(VALID_STATUSES)와 일치한다 — disabled 로 바로 등재 가능."""
    out, token_rel = _make_repo(tmp_path)
    assert _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel,
                "--status", "disabled") == 0
    saved = json.loads(open(out, encoding="utf-8").read())
    assert saved["seats"]["seat-a"]["status"] == "disabled"


@pytest.mark.parametrize("bad", ["seat/a", "seat a", "seat;rm -rf /", "../seat", "seat$(id)", ""])
def test_seat_id_validation(tmp_path, capsys, bad):
    """락 경로 합성 오염 방지 — 형식 위반 seat_id 는 등재/배정 모두 거부."""
    out, token_rel = _make_repo(tmp_path)
    assert _run(out, "register-seat", "--id", bad, "--token-file", token_rel) != 0
    assert not os.path.exists(out)  # 실패는 원장을 만들지 않는다

    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    before = open(out, "rb").read()
    capsys.readouterr()
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", bad) != 0
    assert open(out, "rb").read() == before


def test_set_status_missing_seat(tmp_path, capsys):
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    before = open(out, "rb").read()
    capsys.readouterr()

    assert _run(out, "set-status", "--seat", "없는시트", "--status", "disabled") != 0
    assert "없는시트" in capsys.readouterr().err
    assert open(out, "rb").read() == before  # 실패 시 원장 무변경


# ── ④ 1시트:1워크스페이스 가드 ────────────────────────────────────────────────


def test_assign_one_seat_one_workspace_guard(tmp_path, capsys):
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a")
    before = open(out, "rb").read()
    capsys.readouterr()

    # 같은 시트를 다른 워크스페이스에 → --force 없이는 거부 + 원장 무변경.
    assert _run(out, "assign", "--workspace", "77c0ffee", "--seat", "seat-a") != 0
    assert "seat-a" in capsys.readouterr().err
    assert open(out, "rb").read() == before

    # --force 면 재배정된다(운영자 명시 판단).
    assert _run(out, "assign", "--workspace", "77c0ffee", "--seat", "seat-a", "--force") == 0
    saved = json.loads(open(out, encoding="utf-8").read())
    assert saved["assignments"] == {"3be49b62": "seat-a", "77c0ffee": "seat-a"}


def test_assign_missing_seat(tmp_path, capsys):
    out, _ = _make_repo(tmp_path)
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", "없는시트") != 0
    assert "없는시트" in capsys.readouterr().err
    # 배정만으로 시트를 창작하지 않는다.
    if os.path.exists(out):
        assert json.loads(open(out, encoding="utf-8").read())["seats"] == {}


def test_assign_same_workspace_reassign_allowed(tmp_path, capsys):
    """같은 워크스페이스에 같은 시트를 다시 배정하는 것은 가드 대상이 아니다(멱등)."""
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a")
    capsys.readouterr()
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a") == 0


# ── ⑤ 비밀 위생 — 출력에 토큰 값이 없다 ───────────────────────────────────────


def test_no_secret_in_output(tmp_path, capsys):
    out, token_rel = _make_repo(tmp_path)
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel, "--label", "계정 A")
    _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a")
    capsys.readouterr()

    _run(out, "resolve", "--resolve-key", "3be49b62")
    captured = capsys.readouterr()
    assert TOKEN_VALUE not in captured.out
    assert TOKEN_VALUE not in captured.err

    _run(out, "list")
    captured = capsys.readouterr()
    assert TOKEN_VALUE not in captured.out
    assert "seat-a" in captured.out
    assert ".ralph/seats/seat-a.token" in captured.out  # 경로는 노출해도 무방

    # 원장 파일 자체에도 토큰 값은 담기지 않는다.
    assert TOKEN_VALUE not in open(out, encoding="utf-8").read()


def test_resolve_quotes_shell_metacharacters(tmp_path, capsys):
    """경로에 셸 메타문자가 있어도 eval 안전하게 인용된다."""
    out, token_rel = _make_repo(tmp_path, token_name="seat a;rm -rf x.token")
    _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel)
    _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a")
    capsys.readouterr()

    _run(out, "resolve", "--resolve-key", "3be49b62")
    line = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("SEAT_TOKEN_FILE=")][0]
    value = line.split("=", 1)[1]
    assert value.startswith("'") and value.endswith("'")  # shlex.quote 적용


# ── ⑥ workspaces.json 미접근 ──────────────────────────────────────────────────


def test_works_without_workspaces_ledger(tmp_path, capsys):
    """매핑 원장(.ralph/workspaces.json)이 없어도 전 서브커맨드가 동작한다."""
    out, token_rel = _make_repo(tmp_path)
    workspaces = tmp_path / ".ralph" / "workspaces.json"
    assert not workspaces.exists()

    assert _run(out, "register-seat", "--id", "seat-a", "--token-file", token_rel) == 0
    assert _run(out, "assign", "--workspace", "3be49b62", "--seat", "seat-a") == 0
    assert _run(out, "set-status", "--seat", "seat-a", "--status", "active") == 0
    assert _run(out, "list") == 0
    assert _run(out, "resolve", "--resolve-key", "3be49b62") == 0
    assert "SEAT_ID=seat-a" in capsys.readouterr().out
    # 매핑 원장을 만들지도 읽지도 않는다.
    assert not workspaces.exists()


def test_list_empty_ledger(tmp_path, capsys):
    missing = str(tmp_path / ".ralph" / "seats.json")
    assert _run(missing, "list") == 0
    assert capsys.readouterr().out.strip() != ""


# ── 순수 함수 단위 (파일 I/O 없음) ────────────────────────────────────────────


def test_pure_functions_do_not_mutate_input():
    ledger = sm.empty_ledger(now="2026-08-03T00:00:00Z")
    registered = sm.register_seat(ledger, "seat-a", token_file="t.token")
    assert ledger["seats"] == {}  # 원본 불변
    assigned = sm.assign(registered, "3be49b62", "seat-a")
    assert registered["assignments"] == {}
    disabled = sm.set_status(assigned, "seat-a", "disabled")
    assert assigned["seats"]["seat-a"]["status"] == "active"
    assert disabled["seats"]["seat-a"]["status"] == "disabled"
    # 변경 함수는 updated_at 을 건드리지 않는다(쓰기 직전 stamp 가 단독으로 찍는다).
    assert disabled["updated_at"] == "2026-08-03T00:00:00Z"


def test_stamp_keeps_updated_at_when_unchanged():
    first = sm.stamp(None, sm.empty_ledger(), now="2026-08-01T00:00:00Z")
    same = sm.stamp(first, first, now="2026-08-02T00:00:00Z")
    assert same["updated_at"] == "2026-08-01T00:00:00Z"

    changed = sm.stamp(first, sm.register_seat(first, "seat-a", token_file="t"), now="2026-08-02T00:00:00Z")
    assert changed["updated_at"] == "2026-08-02T00:00:00Z"


def test_assign_invalid_status_rejected():
    ledger = sm.register_seat(sm.empty_ledger(), "seat-a", token_file="t")
    with pytest.raises(ValueError):
        sm.set_status(ledger, "seat-a", "없는상태")


def test_base_dir_for():
    # `<repo>/.ralph/seats.json` → `<repo>` (상대경로 기준점).
    assert sm.base_dir_for("/x/repo/.ralph/seats.json") == "/x/repo"
    # `.ralph` 가 아니면 원장 디렉터리 자체가 기준.
    assert sm.base_dir_for("/x/repo/seats.json") == "/x/repo"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
