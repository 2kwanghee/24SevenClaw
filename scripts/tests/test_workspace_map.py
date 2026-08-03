#!/usr/bin/env python3
"""workspace_map 단위 테스트 (다프로젝트화 P5/F-4).

검증 축:
  1. 신규 원장 생성 — 서버 목록 → 스키마·status·workspace_key 유도.
  2. 멱등 — 같은 입력 2회 = 동일 결과(updated_at 포함) + 수동 repo_source 보존.
  3. pending_source 표기 — repo_source 미확보는 pending_source, 수동 확보 시 mapped.
  4. 접두사→키 해석 — 파이프라인 automap 이 쓰는 resolve_key_for_title 동등 로직.

HTTP 는 호출하지 않는다(build_ledger/resolve_key_for_title 순수 함수 + 로컬 파일).

Usage:
    cd ClickEye && pytest scripts/tests/test_workspace_map.py -v
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import workspace_map as wm  # noqa: E402

# 서버(GET /intake/machine/projects) 응답 형태의 픽스처.
PROJECTS = [
    {
        "intake_id": "3be49b62-1e0c-4b7d-9a11-000000000000",
        "project_id": "aaaaaaaa-0000-0000-0000-000000000000",
        "title": "쇼핑몰 구축",
        "tickets_status": "issued",
        "ticket_prefix": "[수주:3be49b62] ",
    },
    {
        "intake_id": "77c0ffee-2222-4b7d-9a11-000000000000",
        "project_id": "bbbbbbbb-0000-0000-0000-000000000000",
        "title": "예약 시스템",
        "tickets_status": "none",
        "ticket_prefix": "[수주:77c0ffee] ",
    },
]


# ── ① 신규 원장 생성 ─────────────────────────────────────────────────────────


def test_build_new_ledger():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    assert ledger["version"] == 1
    assert ledger["updated_at"] == "2026-08-01T00:00:00Z"
    ws = ledger["workspaces"]
    assert set(ws) == {"[수주:3be49b62] ", "[수주:77c0ffee] "}
    entry = ws["[수주:3be49b62] "]
    # workspace_key 는 intake_id 앞 8자로 유도(접두사 규약과 일치).
    assert entry["workspace_key"] == "3be49b62"
    assert entry["intake_id"] == "3be49b62-1e0c-4b7d-9a11-000000000000"
    assert entry["project_id"] == "aaaaaaaa-0000-0000-0000-000000000000"
    # 서버는 repo_source 를 주지 않는다 → 미확보 → pending_source.
    assert entry["repo_source"] is None
    assert entry["status"] == "pending_source"


# ── ② 멱등 + 수동 repo_source 보존 ───────────────────────────────────────────


def test_idempotent_and_manual_source_preserved():
    first = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    # 운영자가 저장된 원장의 한 항목에 repo_source 를 수동 기입(status 는 손대지 않음).
    first["workspaces"]["[수주:3be49b62] "]["repo_source"] = "git@github.com:acme/shop.git"

    # 재빌드: 수동 repo_source 보존 + status 가 mapped 로 승격(실제 내용 변화 → updated_at 갱신).
    second = wm.build_ledger(PROJECTS, existing=first, now="2026-08-02T00:00:00Z")
    entry = second["workspaces"]["[수주:3be49b62] "]
    assert entry["repo_source"] == "git@github.com:acme/shop.git"  # 폴링이 덮어쓰지 않음
    assert entry["status"] == "mapped"  # 소스 확보 → mapped
    assert second["updated_at"] == "2026-08-02T00:00:00Z"

    # 안정화된 이후로는 완전 멱등: 같은 입력 재빌드 = 바이트 단위 동일 + updated_at 유지.
    third = wm.build_ledger(PROJECTS, existing=second, now="2026-08-03T00:00:00Z")
    assert third == second
    assert third["updated_at"] == "2026-08-02T00:00:00Z"  # 내용 불변 → 시각도 유지


# ── ③ pending_source 표기 (소스 미확보) ──────────────────────────────────────


def test_pending_source_marking():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    statuses = {p["ticket_prefix"]: ledger["workspaces"][p["ticket_prefix"]]["status"] for p in PROJECTS}
    assert statuses == {
        "[수주:3be49b62] ": "pending_source",
        "[수주:77c0ffee] ": "pending_source",
    }
    # 서버가 더는 반환하지 않는 선등록 항목도 삭제하지 않는다(수동/선등록 보존).
    existing = {
        "version": 1,
        "updated_at": "2026-07-01T00:00:00Z",
        "workspaces": {
            "[수주:deadbeef] ": {
                "workspace_key": "deadbeef",
                "intake_id": "deadbeef-0000-0000-0000-000000000000",
                "project_id": None,
                "repo_source": "https://example.com/preregistered.git",
                "status": "mapped",
            }
        },
    }
    merged = wm.build_ledger(PROJECTS, existing=existing, now="2026-08-01T00:00:00Z")
    assert "[수주:deadbeef] " in merged["workspaces"]  # 선등록 보존
    assert len(merged["workspaces"]) == 3


# ── ④ 접두사→키 해석 (파이프라인 automap) ────────────────────────────────────


def test_resolve_key_for_title():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    # 전부 pending_source 상태 → 해석 불가(self-repo 폴백).
    assert wm.resolve_key_for_title(ledger, "[수주:3be49b62] 회원가입 구현") == ""

    # 소스 확보(mapped)된 항목만 해석된다.
    ledger["workspaces"]["[수주:3be49b62] "]["repo_source"] = "git@x:acme/shop.git"
    ledger["workspaces"]["[수주:3be49b62] "]["status"] = "mapped"
    assert wm.resolve_key_for_title(ledger, "[수주:3be49b62] 회원가입 구현") == "3be49b62"
    # 접두사 불일치 / 원장 없음 → 빈 문자열.
    assert wm.resolve_key_for_title(ledger, "CE-401 일반 티켓") == ""
    assert wm.resolve_key_for_title(None, "[수주:3be49b62] 무엇") == ""


# ── CLI 스모크: --resolve-title 오프라인 모드(네트워크·서비스 키 불요) ────────


def test_cli_resolve_title(tmp_path, capsys):
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    ledger["workspaces"]["[수주:3be49b62] "]["repo_source"] = "git@x:acme/shop.git"
    ledger["workspaces"]["[수주:3be49b62] "]["status"] = "mapped"
    out = tmp_path / "workspaces.json"
    out.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    rc = wm.main(["--resolve-title", "[수주:3be49b62] 무언가", "--output", str(out)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "3be49b62"


# ── ⑤ set_source: 수동 기입 + mapped 전환 (순수 함수) ─────────────────────────


def test_set_source_by_prefix():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    new_ledger = wm.set_source(ledger, "[수주:3be49b62] ", "git@github.com:acme/shop.git")

    entry = new_ledger["workspaces"]["[수주:3be49b62] "]
    assert entry["repo_source"] == "git@github.com:acme/shop.git"
    assert entry["status"] == "mapped"
    # 다른 항목은 불변.
    other = new_ledger["workspaces"]["[수주:77c0ffee] "]
    assert other == ledger["workspaces"]["[수주:77c0ffee] "]
    # 원본 ledger 는 변경되지 않는다(순수 함수).
    assert ledger["workspaces"]["[수주:3be49b62] "]["repo_source"] is None
    assert ledger["workspaces"]["[수주:3be49b62] "]["status"] == "pending_source"


def test_set_source_by_workspace_key():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    new_ledger = wm.set_source(ledger, "3be49b62", "git@github.com:acme/shop.git")

    entry = new_ledger["workspaces"]["[수주:3be49b62] "]
    assert entry["repo_source"] == "git@github.com:acme/shop.git"
    assert entry["status"] == "mapped"


def test_set_source_idempotent():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    first = wm.set_source(ledger, "3be49b62", "git@github.com:acme/shop.git")
    second = wm.set_source(first, "3be49b62", "git@github.com:acme/shop.git")
    # updated_at 포함 완전 동일 — set_source 는 updated_at 을 건드리지 않는다.
    assert first == second
    assert first["updated_at"] == ledger["updated_at"]


def test_set_source_missing_key_raises():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    with pytest.raises(KeyError):
        wm.set_source(ledger, "존재하지않는키", "git@x:acme/shop.git")
    # 존재하지 않는 키로 새 항목을 창작하지 않는다.
    assert set(ledger["workspaces"]) == {"[수주:3be49b62] ", "[수주:77c0ffee] "}


# ── ⑥ set_source 후 build_ledger 재폴링 — 수동 값 보존 회귀 방지 ───────────────


def test_set_source_then_rebuild_preserves_mapping():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    mapped = wm.set_source(ledger, "3be49b62", "git@github.com:acme/shop.git")

    rebuilt = wm.build_ledger(PROJECTS, existing=mapped, now="2026-08-02T00:00:00Z")
    entry = rebuilt["workspaces"]["[수주:3be49b62] "]
    assert entry["repo_source"] == "git@github.com:acme/shop.git"
    assert entry["status"] == "mapped"


def test_set_source_then_resolve_key_for_title():
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    mapped = wm.set_source(ledger, "3be49b62", "git@github.com:acme/shop.git")
    assert wm.resolve_key_for_title(mapped, "[수주:3be49b62] 회원가입 구현") == "3be49b62"


# ── CLI 스모크: --set-source / --list 오프라인 모드 ────────────────────────────


def test_cli_set_source_success(tmp_path, capsys):
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    out = tmp_path / "workspaces.json"
    out.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    rc = wm.main(
        ["--set-source", "3be49b62", "git@github.com:acme/shop.git", "--output", str(out)]
    )
    assert rc == 0
    err = capsys.readouterr().err
    assert "3be49b62" in err

    saved = json.loads(out.read_text(encoding="utf-8"))
    entry = saved["workspaces"]["[수주:3be49b62] "]
    assert entry["repo_source"] == "git@github.com:acme/shop.git"
    assert entry["status"] == "mapped"

    # --resolve-title 이 workspace_key 를 반환하는지 확인.
    rc2 = wm.main(["--resolve-title", "[수주:3be49b62] 무언가", "--output", str(out)])
    assert rc2 == 0
    assert capsys.readouterr().out.strip() == "3be49b62"


def test_cli_set_source_idempotent_bytes(tmp_path):
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    out = tmp_path / "workspaces.json"
    out.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    rc1 = wm.main(
        ["--set-source", "3be49b62", "git@github.com:acme/shop.git", "--output", str(out)]
    )
    assert rc1 == 0
    first_bytes = out.read_bytes()

    rc2 = wm.main(
        ["--set-source", "3be49b62", "git@github.com:acme/shop.git", "--output", str(out)]
    )
    assert rc2 == 0
    second_bytes = out.read_bytes()
    assert first_bytes == second_bytes


def test_cli_set_source_missing_ledger(tmp_path, capsys):
    missing = tmp_path / "no_such_ledger.json"
    rc = wm.main(
        ["--set-source", "3be49b62", "git@github.com:acme/shop.git", "--output", str(missing)]
    )
    assert rc != 0
    assert not missing.exists()
    assert "ERROR" in capsys.readouterr().err


def test_cli_set_source_missing_key(tmp_path, capsys):
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    out = tmp_path / "workspaces.json"
    out.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    original_bytes = out.read_bytes()

    rc = wm.main(
        ["--set-source", "존재하지않는키", "git@x:acme/shop.git", "--output", str(out)]
    )
    assert rc != 0
    err = capsys.readouterr().err
    assert "존재하지않는키" in err
    # 실패 시 원장 파일은 절대 쓰지 않는다.
    assert out.read_bytes() == original_bytes


def test_cli_list(tmp_path, capsys):
    ledger = wm.build_ledger(PROJECTS, existing=None, now="2026-08-01T00:00:00Z")
    out = tmp_path / "workspaces.json"
    out.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    rc = wm.main(["--list", "--output", str(out)])
    assert rc == 0
    stdout = capsys.readouterr().out
    assert "[수주:3be49b62] " in stdout
    assert "[수주:77c0ffee] " in stdout
    assert "pending_source" in stdout


def test_cli_list_missing_ledger(tmp_path, capsys):
    missing = tmp_path / "no_such_ledger.json"
    rc = wm.main(["--list", "--output", str(missing)])
    # 조회 실패는 비차단 원칙 — 항상 0.
    assert rc == 0
    assert capsys.readouterr().out.strip() != ""


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
