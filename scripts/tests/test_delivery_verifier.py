"""딜리버리 정합성 검증기 테스트 (다프로젝트화 P7).

검증 축:
  1. 완주 분류 — Done/흡수(Canceled·Duplicate)/잔존, **미지 issue_id 는 잔존**
     (상태를 모르는 티켓을 완료로 가정하면 미완주가 통과로 위장된다 — fail-closed).
  2. 게이트 실행 — 실제 서브프로세스(true/false/echo)로 전량 실행·타임아웃·출력 꼬리.
     fail-fast 없음(뒤 게이트의 실패를 숨기지 않는다).
  3. 리포트 — 흡수 티켓 명시·실패 게이트 출력 포함·상한 절단.
  4. CLI exit 계약 — 0/3/4/5/2. 배치(delivery_verify.sh)가 이 코드로 분기한다.

Usage:
    cd ClickEye && pytest scripts/tests/test_delivery_verifier.py -v
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import delivery_verifier as dv  # noqa: E402

LEDGER = [
    {"key": "T1", "identifier": "CE-901", "issue_id": "iid-1", "title": "설계"},
    {"key": "T2", "identifier": "CE-902", "issue_id": "iid-2", "title": "구현"},
    {"key": "T3", "identifier": "CE-903", "issue_id": "iid-3", "title": "테스트"},
]


# ── 1. 완주 분류 ────────────────────────────────────────────────────────────


def test_all_done_is_complete():
    c = dv.classify_completion(LEDGER, {"iid-1": "Done", "iid-2": "Done", "iid-3": "Done"})
    assert c["complete"] is True
    assert c["done"] == ["CE-901", "CE-902", "CE-903"] and c["remaining"] == []


def test_absorbed_counts_as_complete_but_is_visible():
    """Canceled/Duplicate 는 완주 인정 — 단 리포트에 명시된다(숨은 미구현 방지)."""
    c = dv.classify_completion(
        LEDGER, {"iid-1": "Done", "iid-2": "Canceled", "iid-3": "Duplicate"}
    )
    assert c["complete"] is True
    assert c["absorbed"] == ["CE-902(Canceled)", "CE-903(Duplicate)"]
    report = dv.build_report(c, [])
    assert "흡수 2건" in report and "CE-902(Canceled)" in report


@pytest.mark.parametrize("state", ["Queued", "In Progress", "Backlog", "NightQueued"])
def test_nonterminal_state_blocks_completion(state):
    c = dv.classify_completion(LEDGER, {"iid-1": "Done", "iid-2": state, "iid-3": "Done"})
    assert c["complete"] is False
    assert c["remaining"] == [{"identifier": "CE-902", "state": state}]


def test_unknown_issue_id_is_remaining_not_done():
    """조회 누락(삭제·권한·API 오류)은 잔존 — 모르는 것을 완료로 가정하지 않는다."""
    c = dv.classify_completion(LEDGER, {"iid-1": "Done", "iid-3": "Done"})  # iid-2 누락
    assert c["complete"] is False
    assert c["remaining"] == [{"identifier": "CE-902", "state": "UNKNOWN"}]


def test_state_type_wins_over_name(monkeypatch=None):
    """E2E 실증 결함 회귀 테스트: 팀 커스텀 완료 상태(Confirm, type=completed)를
    이름 셋에 없어도 완주로 인정한다 — type 이 있으면 type 이 우선."""
    states = {
        "iid-1": {"name": "Done", "type": "completed"},
        "iid-2": {"name": "Confirm", "type": "completed"},   # 커스텀 완료명
        "iid-3": {"name": "Dropped", "type": "canceled"},    # 커스텀 취소명
    }
    c = dv.classify_completion(LEDGER, states)
    assert c["complete"] is True
    assert c["done"] == ["CE-901", "CE-902"]
    assert c["absorbed"] == ["CE-903(Dropped)"]


def test_type_aware_nonterminal_remains():
    states = {
        "iid-1": {"name": "Done", "type": "completed"},
        "iid-2": {"name": "Queued", "type": "unstarted"},
        "iid-3": {"name": "Done", "type": "completed"},
    }
    c = dv.classify_completion(LEDGER, states)
    assert c["complete"] is False
    assert c["remaining"] == [{"identifier": "CE-902", "state": "Queued"}]


# ── 2. 게이트 실행 (실 서브프로세스 — 목킹 없음) ─────────────────────────────


def test_gates_run_all_and_collect_results(tmp_path):
    """실패가 있어도 전량 실행 — 뒤 게이트의 결과를 숨기지 않는다."""
    results = dv.run_gates(
        ["echo gate-one", "false", "echo gate-three"], workdir=str(tmp_path)
    )
    assert [g["exit"] for g in results] == [0, 1, 0]
    assert "gate-one" in results[0]["tail"]
    assert "gate-three" in results[2]["tail"]  # 실패(false) 뒤에도 실행됐다


def test_gate_timeout_is_failure(tmp_path):
    results = dv.run_gates(["sleep 5"], workdir=str(tmp_path), timeout=1)
    assert results[0]["timed_out"] is True and results[0]["exit"] != 0
    assert "타임아웃" in results[0]["tail"]


def test_gate_runs_in_workdir(tmp_path):
    (tmp_path / "marker.txt").write_text("here", encoding="utf-8")
    results = dv.run_gates(["cat marker.txt"], workdir=str(tmp_path))
    assert results[0]["exit"] == 0 and "here" in results[0]["tail"]


# ── 3. 리포트 ───────────────────────────────────────────────────────────────


def test_report_includes_failed_gate_tail_and_caps_length():
    completion = dv.classify_completion(LEDGER, dict.fromkeys(["iid-1", "iid-2", "iid-3"], "Done"))
    gates = [
        {"cmd": "./gradlew check", "exit": 1, "timed_out": False, "tail": "ArchUnit 위반 3건\n" + "x" * 30000},
        {"cmd": "npm test", "exit": 0, "timed_out": False, "tail": "ok"},
    ]
    report = dv.build_report(completion, gates)
    assert "❌ gate `./gradlew check` → exit 1" in report
    assert "ArchUnit 위반" in report
    assert "✅ gate `npm test` → exit 0" in report
    assert len(report) <= dv.REPORT_MAX  # 서버 스키마 상한과 일치


# ── 4. CLI exit 계약 ────────────────────────────────────────────────────────


def _run_cli(tmp_path, ledger, states, gates_lines=None, extra=None, monkeypatch=None):
    """CLI 를 in-process 로 실행(원격은 fetch_states 목킹). exit 코드와 stdout JSON 반환."""
    ledger_file = tmp_path / "ledger.json"
    ledger_file.write_text(json.dumps({"tickets": ledger}), encoding="utf-8")
    argv = ["delivery_verifier", "--ledger", str(ledger_file), "--workdir", str(tmp_path)]
    if gates_lines is not None:
        gf = tmp_path / "gates.txt"
        gf.write_text("\n".join(gates_lines), encoding="utf-8")
        argv += ["--gates-file", str(gf)]
    argv += extra or []
    monkeypatch.setattr(dv, "fetch_states", lambda ids: states)
    monkeypatch.setattr(sys, "argv", argv)

    import contextlib
    import io

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = dv.main()
    return rc, json.loads(out.getvalue())


ALL_DONE = {"iid-1": "Done", "iid-2": "Done", "iid-3": "Done"}


def test_cli_verified_exit_0(tmp_path, monkeypatch):
    rc, res = _run_cli(tmp_path, LEDGER, ALL_DONE, gates_lines=["true", "echo ok"],
                       monkeypatch=monkeypatch)
    assert rc == dv.EXIT_VERIFIED
    assert res["verdict"] == "verified" and res["passed"] is True
    assert res["report"]  # 증거 비어있지 않음 — 서버가 빈 report 를 거부한다


def test_cli_incomplete_exit_3_no_gates_run(tmp_path, monkeypatch):
    states = {"iid-1": "Done", "iid-2": "In Progress", "iid-3": "Done"}
    rc, res = _run_cli(tmp_path, LEDGER, states, gates_lines=["false"],
                       monkeypatch=monkeypatch)
    assert rc == dv.EXIT_INCOMPLETE
    assert res["verdict"] == "incomplete" and res["passed"] is None
    assert "CE-902=In Progress" in res["report"]  # 미완주면 게이트(false) 미실행


def test_cli_gate_failed_exit_4(tmp_path, monkeypatch):
    rc, res = _run_cli(tmp_path, LEDGER, ALL_DONE, gates_lines=["true", "false"],
                       monkeypatch=monkeypatch)
    assert rc == dv.EXIT_GATE_FAILED
    assert res["verdict"] == "gate_failed" and res["passed"] is False


def test_cli_no_gates_exit_5_never_passes(tmp_path, monkeypatch):
    """게이트 부재 = 검증 불가 — passed 가 true 로 위장되지 않는다."""
    rc, res = _run_cli(tmp_path, LEDGER, ALL_DONE, gates_lines=["# 주석뿐"],
                       monkeypatch=monkeypatch)
    assert rc == dv.EXIT_NO_GATES
    assert res["verdict"] == "no_gates" and res["passed"] is None
    assert "검증 불가" in res["report"]


def test_cli_check_only_skips_gates(tmp_path, monkeypatch):
    rc, res = _run_cli(tmp_path, LEDGER, ALL_DONE, gates_lines=["false"],
                       extra=["--check-only"], monkeypatch=monkeypatch)
    assert rc == dv.EXIT_VERIFIED and res["verdict"] == "complete"
    assert res["passed"] is None  # 판정 없음 — 관측만


def test_cli_bad_ledger_exit_2(tmp_path, monkeypatch):
    bad = tmp_path / "bad.json"
    bad.write_text('{"tickets": [{"no_issue_id": 1}]}', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["delivery_verifier", "--ledger", str(bad)])
    assert dv.main() == 2


def test_cli_exit_codes_are_distinct():
    """배치 분기의 전제 — 네 코드가 서로 달라야 한다."""
    codes = {dv.EXIT_VERIFIED, dv.EXIT_INCOMPLETE, dv.EXIT_GATE_FAILED, dv.EXIT_NO_GATES}
    assert len(codes) == 4 and 2 not in codes  # 2는 입력 오류 전용
