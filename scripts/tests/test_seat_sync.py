#!/usr/bin/env python3
"""seat_sync 단위 테스트 (CE-400).

검증 축:
  1. 성공 동기화 — 신규 active 시트 등록, 토큰 파일 권한 0600.
  2. 기존 수동 시트("seat-a")는 API 응답에 없으면 그대로 보존.
  3. DB blocked 시트가 로컬에 이미 있으면 disabled 로 전환.
  4. DB blocked 시트가 로컬에 없으면 생성하지 않고 스킵.
  5. API 실패 시 기존 원장 파일 무변경.
  6. 토큰 값이 stdout/stderr 어디에도 노출되지 않는다.

네트워크 호출 없음(urlopen monkeypatch).
"""

from __future__ import annotations

import json
import os
import stat
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seat_map as sm  # noqa: E402
import seat_sync as ss  # noqa: E402

SECRET_TOKEN = "sk-ant-oat01-절대노출금지-비밀토큰"


class _FakeResp:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _provision_body(seats: list[dict]) -> bytes:
    return json.dumps({"seats": seats}).encode("utf-8")


def _seat_item(seat_id: str, *, email: str, status: str, token: str = SECRET_TOKEN) -> dict:
    return {
        "seat_id": seat_id,
        "user_id": "11111111-1111-1111-1111-111111111111",
        "email": email,
        "seat_status": status,
        "token": token,
    }


ACTIVE_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
BLOCKED_UUID = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
UNKNOWN_BLOCKED_UUID = "cccccccc-dddd-eeee-ffff-000000000000"


def _run(monkeypatch, tmp_path, items, output=None):
    output = output or str(tmp_path / ".ralph" / "seats.json")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")

    def fake_urlopen(req, timeout=None):
        return _FakeResp(_provision_body(items))

    monkeypatch.setattr(ss, "urlopen", fake_urlopen)
    rc = ss.main(["--output", output])
    return rc, output


# ── ① 성공 동기화: 신규 active 등록 + 토큰 파일 0600 ─────────────────────────


def test_sync_registers_new_active_seat_with_secure_perms(monkeypatch, tmp_path):
    items = [_seat_item(ACTIVE_UUID, email="a@example.com", status="active")]
    rc, output = _run(monkeypatch, tmp_path, items)
    assert rc == 0

    ledger = json.loads(open(output, encoding="utf-8").read())
    assert ACTIVE_UUID in ledger["seats"]
    entry = ledger["seats"][ACTIVE_UUID]
    assert entry["status"] == "active"
    assert entry["label"] == "a@example.com"

    token_file_rel = entry["auth"]["oauth_token_file"]
    repo_root = sm.base_dir_for(output)
    abs_token_path = os.path.join(repo_root, token_file_rel)
    assert os.path.isfile(abs_token_path)
    mode = stat.S_IMODE(os.stat(abs_token_path).st_mode)
    assert mode == 0o600
    with open(abs_token_path, encoding="utf-8") as fh:
        assert fh.read() == SECRET_TOKEN


# ── ② 기존 수동 시트는 API 응답에 없으면 보존 ────────────────────────────────


def test_manual_seat_not_in_response_is_untouched(monkeypatch, tmp_path):
    output = str(tmp_path / ".ralph" / "seats.json")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    manual_ledger = sm.register_seat(
        sm.empty_ledger(), "seat-a", token_file=".ralph/seats/seat-a.token", label="수동 계정"
    )
    sm.write_ledger(output, sm.stamp(None, manual_ledger))

    items = [_seat_item(ACTIVE_UUID, email="a@example.com", status="active")]
    rc, output = _run(monkeypatch, tmp_path, items, output=output)
    assert rc == 0

    ledger = json.loads(open(output, encoding="utf-8").read())
    assert "seat-a" in ledger["seats"]
    assert ledger["seats"]["seat-a"]["status"] == "active"
    assert ledger["seats"]["seat-a"]["label"] == "수동 계정"
    assert ACTIVE_UUID in ledger["seats"]


# ── ③ DB blocked 시트가 로컬에 이미 있으면 disabled 로 전환 ──────────────────


def test_existing_local_seat_set_disabled_when_db_blocked(monkeypatch, tmp_path):
    output = str(tmp_path / ".ralph" / "seats.json")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    pre_ledger = sm.register_seat(
        sm.empty_ledger(),
        BLOCKED_UUID,
        token_file=".ralph/seats/prev.token",
        status="active",
    )
    sm.write_ledger(output, sm.stamp(None, pre_ledger))

    items = [_seat_item(BLOCKED_UUID, email="b@example.com", status="blocked")]
    rc, output = _run(monkeypatch, tmp_path, items, output=output)
    assert rc == 0

    ledger = json.loads(open(output, encoding="utf-8").read())
    assert ledger["seats"][BLOCKED_UUID]["status"] == "disabled"


# ── ④ DB blocked 시트가 로컬에 없으면 생성하지 않는다 ────────────────────────


def test_unknown_blocked_seat_not_created(monkeypatch, tmp_path):
    items = [_seat_item(UNKNOWN_BLOCKED_UUID, email="c@example.com", status="blocked")]
    rc, output = _run(monkeypatch, tmp_path, items)
    assert rc == 0

    ledger = json.loads(open(output, encoding="utf-8").read())
    assert UNKNOWN_BLOCKED_UUID not in ledger["seats"]


# ── ⑤ API 실패 시 기존 원장 무변경 ───────────────────────────────────────────


def test_api_failure_leaves_existing_ledger_unchanged(monkeypatch, tmp_path):
    output = str(tmp_path / ".ralph" / "seats.json")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    pre_ledger = sm.register_seat(
        sm.empty_ledger(), "seat-a", token_file=".ralph/seats/seat-a.token"
    )
    sm.write_ledger(output, sm.stamp(None, pre_ledger))
    before = open(output, encoding="utf-8").read()

    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")

    def boom(req, timeout=None):
        raise OSError("네트워크 다운")

    monkeypatch.setattr(ss, "urlopen", boom)
    rc = ss.main(["--output", output])
    assert rc == 1

    after = open(output, encoding="utf-8").read()
    assert before == after


def test_missing_base_url_leaves_ledger_unchanged_and_exits_1(monkeypatch, tmp_path):
    output = str(tmp_path / ".ralph" / "seats.json")
    monkeypatch.delenv("FLOWOPS_GOVERNANCE_SERVICE_URL", raising=False)
    monkeypatch.delenv("API_URL", raising=False)
    rc = ss.main(["--output", output])
    assert rc == 1
    assert not os.path.exists(output)


# ── ⑥ 토큰 값이 stdout/stderr 에 노출되지 않는다 ─────────────────────────────


def test_token_value_never_appears_in_output(monkeypatch, tmp_path, capsys):
    items = [
        _seat_item(ACTIVE_UUID, email="a@example.com", status="active"),
        _seat_item(BLOCKED_UUID, email="b@example.com", status="blocked"),
    ]
    _run(monkeypatch, tmp_path, items)
    captured = capsys.readouterr()
    assert SECRET_TOKEN not in captured.out
    assert SECRET_TOKEN not in captured.err
