"""시트 잔량 스냅샷 인제스트 스크립트 테스트 (CE-387).

검증 축:
  1. cswap stdout(JSON) → 배치 payload 빌드(순수 함수) — 정상/파싱실패/accounts 부재.
  2. cswap 명령 부재(FileNotFoundError) → run_cswap None, main() exit 0(전송 안 함).
  3. 전송(urlopen monkeypatch — 실제 네트워크 금지).

Usage:
    cd ClickEye && pytest scripts/tests/test_seat_quota_ingest.py -v
"""

from __future__ import annotations

import json
import os
import sys

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import seat_quota_ingest as sqi  # noqa: E402


def _cswap_json():
    return json.dumps(
        {
            "schemaVersion": 1,
            "accounts": [
                {
                    "number": 1,
                    "email": "a@example.com",
                    "organizationName": "Org A",
                    "organizationUuid": "org-1",
                    "active": True,
                    "usageStatus": "ok",
                    "usageFetchedAt": "2026-08-05T00:00:00Z",
                    "usage": {
                        "fiveHour": {"pct": 12.5, "resetsAt": "2026-08-05T05:00:00Z"},
                        "sevenDay": {
                            "pct": 30.0,
                            "resetsAt": "2026-08-10T00:00:00Z",
                            "expectedPct": 28.0,
                            "aheadOfPace": True,
                            "projectedExhaustionAt": None,
                            "willLastToReset": True,
                        },
                        "scoped": [
                            {
                                "name": "claude-sonnet-5",
                                "pct": 5.0,
                                "resetsAt": "2026-08-06T00:00:00Z",
                                "expectedPct": 4.0,
                                "aheadOfPace": True,
                                "projectedExhaustionAt": None,
                                "willLastToReset": True,
                            }
                        ],
                    },
                }
            ],
        }
    )


# ── 1. payload 빌드 ──────────────────────────────────────────────────────────


def test_build_payload_parses_accounts():
    payload = sqi.build_payload(_cswap_json())
    assert payload is not None
    assert len(payload["accounts"]) == 1
    assert payload["accounts"][0]["email"] == "a@example.com"


def test_build_payload_returns_none_on_bad_json():
    assert sqi.build_payload("{잘못된 json") is None


def test_build_payload_returns_none_when_accounts_missing():
    assert sqi.build_payload(json.dumps({"schemaVersion": 1})) is None


def test_build_payload_returns_none_when_accounts_empty():
    assert sqi.build_payload(json.dumps({"accounts": []})) is None


def test_build_payload_returns_none_when_not_object():
    assert sqi.build_payload(json.dumps([1, 2, 3])) is None


# ── 2. cswap 부재 ────────────────────────────────────────────────────────────


def test_run_cswap_returns_none_when_binary_missing(monkeypatch):
    def fake_run(*a, **k):
        raise FileNotFoundError("cswap not found")

    monkeypatch.setattr(sqi.subprocess, "run", fake_run)
    assert sqi.run_cswap() is None


def test_main_exit_zero_when_cswap_missing(monkeypatch):
    def fake_run(*a, **k):
        raise FileNotFoundError("cswap not found")

    monkeypatch.setattr(sqi.subprocess, "run", fake_run)
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")
    monkeypatch.setattr(
        sqi, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("전송 금지"))
    )
    assert sqi.main() == 0


def test_run_cswap_returns_none_on_nonzero_exit(monkeypatch):
    class _Proc:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(sqi.subprocess, "run", lambda *a, **k: _Proc())
    assert sqi.run_cswap() is None


# ── 3. 전송(urlopen monkeypatch) ─────────────────────────────────────────────


class _FakeResp:
    def __init__(self, body=b'{"rows_created":3,"accounts_processed":1,"accounts_skipped":0}'):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_post_snapshots_sends_expected_request(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["data"] = req.data
        captured["headers"] = dict(req.header_items())
        captured["timeout"] = timeout
        return _FakeResp()

    monkeypatch.setattr(sqi, "urlopen", fake_urlopen)
    payload = {"accounts": []}
    body = sqi.post_snapshots(payload, "http://gov:8000", token="tok-123", timeout=5)
    assert "rows_created" in body
    assert captured["url"] == "http://gov:8000/api/v1/ops/seat-quota/snapshots"
    assert captured["method"] == "POST"
    assert json.loads(captured["data"].decode()) == payload
    hdr = {k.lower(): v for k, v in captured["headers"].items()}
    assert hdr.get("x-governance-token") == "tok-123"
    assert hdr.get("content-type") == "application/json"


def test_main_exit_zero_on_send_failure(monkeypatch):
    monkeypatch.setattr(sqi, "run_cswap", lambda: _cswap_json())
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")

    def boom(req, timeout=None):
        raise OSError("네트워크 다운")

    monkeypatch.setattr(sqi, "urlopen", boom)
    assert sqi.main() == 0


def test_main_exit_zero_when_base_url_missing(monkeypatch):
    monkeypatch.setattr(sqi, "run_cswap", lambda: _cswap_json())
    monkeypatch.delenv("FLOWOPS_GOVERNANCE_SERVICE_URL", raising=False)
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.setattr(
        sqi, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("전송 금지"))
    )
    assert sqi.main() == 0
