#!/usr/bin/env python3
"""pipeline_metrics 단위 테스트 — append 스키마·불량 JSON raw·디렉터리 생성·실패 비차단."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pipeline_metrics as pm  # noqa: E402


def _read_jsonl(path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# ── ① 정상 append + 스키마 필드 검증 ─────────────────────────────────────────


def test_append_schema(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    rc = pm.main(["--run-id", "CE-901_20260731_120000", "--event", "impl_done",
                  "--data", '{"duration_s": 42, "workdir": "self"}',
                  "--ledger", str(ledger)])
    assert rc == 0
    rows = _read_jsonl(ledger)
    assert len(rows) == 1
    row = rows[0]
    assert row["version"] == 1
    assert row["run_id"] == "CE-901_20260731_120000"
    assert row["event"] == "impl_done"
    assert row["data"] == {"duration_s": 42, "workdir": "self"}
    # ts 는 ISO8601 UTC(Z 접미)
    assert row["ts"].endswith("Z") and "T" in row["ts"]

    # 두 번째 append 는 같은 파일에 누적
    pm.main(["--run-id", "CE-901_20260731_120000", "--event", "run_done",
             "--data", '{"outcome": "merged"}', "--ledger", str(ledger)])
    rows = _read_jsonl(ledger)
    assert len(rows) == 2
    assert rows[1]["event"] == "run_done"


# ── ② 불량 JSON data → raw 감싸 기록 + exit 0 ────────────────────────────────


def test_bad_json_wrapped(tmp_path, capsys):
    ledger = tmp_path / "runs.jsonl"
    rc = pm.main(["--run-id", "R1", "--event", "refine_done",
                  "--data", "{not valid json", "--ledger", str(ledger)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "불량 JSON" in err
    rows = _read_jsonl(ledger)
    assert rows[0]["data"] == {"raw": "{not valid json"}


def test_non_object_json_wrapped(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    pm.main(["--run-id", "R1", "--event", "e", "--data", "[1,2,3]", "--ledger", str(ledger)])
    rows = _read_jsonl(ledger)
    assert rows[0]["data"] == {"raw": [1, 2, 3]}


# ── ③ 로그 디렉터리 자동 생성 ────────────────────────────────────────────────


def test_dir_autocreate(tmp_path):
    ledger = tmp_path / "nested" / "deep" / "runs.jsonl"
    assert not ledger.parent.exists()
    rc = pm.main(["--run-id", "R1", "--event", "e", "--data", "{}", "--ledger", str(ledger)])
    assert rc == 0
    assert ledger.exists()
    assert len(_read_jsonl(ledger)) == 1


# ── ④ 쓰기 불가 경로에서도 exit 0(비차단) ────────────────────────────────────


def test_unwritable_path_nonblocking(tmp_path, capsys):
    # 존재하는 '파일'을 원장 경로의 부모로 지정 → makedirs 실패 유발
    afile = tmp_path / "iamfile"
    afile.write_text("x", encoding="utf-8")
    ledger = afile / "runs.jsonl"  # afile 이 디렉터리가 아니므로 생성 불가
    rc = pm.main(["--run-id", "R1", "--event", "e", "--data", "{}", "--ledger", str(ledger)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "실패" in err  # 경고는 남기되 죽지 않는다


def test_empty_data_defaults_to_empty_dict(tmp_path):
    ledger = tmp_path / "runs.jsonl"
    pm.main(["--run-id", "R1", "--event", "e", "--ledger", str(ledger)])
    rows = _read_jsonl(ledger)
    assert rows[0]["data"] == {}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
