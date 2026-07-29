"""로컬 배치 사용량 인제스트 모듈 테스트 (CE-328).

검증 축:
  1. 파싱 — stderr 혼입(비-JSON) 줄 스킵, 마지막 result 이벤트 채택,
     result 이벤트 부재 시 None.
  2. modelUsage — 다중 모델을 모델별 항목으로 변환(camelCase 토큰 매핑),
     modelUsage 부재 시 top-level usage 폴백(단일 모델).
  3. key_source — init 이벤트 apiKeySource 유도('none'→subscription_seat,
     그 외→org_api_key, 미확인→subscription_seat).
  4. payload — env(CLICKEYE_SEAT_ID/PROJECT_ID) 반영, meta 보존, 계약 형태.
  5. 전송 — urlopen monkeypatch(실제 네트워크 금지), 실패 시 main() exit 0.

Usage:
    cd ClickEye && pytest scripts/tests/test_usage_ingest.py -v
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import usage_ingest as ui  # noqa: E402


# ── 픽스처 ───────────────────────────────────────────────────────────────────


def _init_line(api_key_source="none"):
    return json.dumps({"type": "system", "subtype": "init", "apiKeySource": api_key_source})


def _result_line(**over):
    evt = {
        "type": "result",
        "session_id": "sess-abc",
        "num_turns": 12,
        "duration_ms": 8993,
        "total_cost_usd": 0.35,
        "modelUsage": {
            "claude-sonnet-5": {
                "inputTokens": 2,
                "outputTokens": 378,
                "cacheReadInputTokens": 23972,
                "cacheCreationInputTokens": 57608,
            }
        },
    }
    evt.update(over)
    return json.dumps(evt)


# ── 1. 파싱 ──────────────────────────────────────────────────────────────────


def test_parse_skips_noise_and_picks_last_result():
    log = "\n".join(
        [
            "그냥 stderr 로그 한 줄",  # 비-JSON 노이즈
            _init_line("none"),
            "{잘못된 json",  # 깨진 JSON
            _result_line(session_id="old"),
            "WARN: 중간 경고",
            _result_line(session_id="sess-final"),
        ]
    )
    result, aks = ui.parse_log(log)
    assert result is not None
    assert result["session_id"] == "sess-final"  # 마지막 result 채택
    assert aks == "none"


def test_parse_no_result_event_returns_none():
    log = "\n".join(["노이즈", _init_line("none"), "또 노이즈"])
    result, aks = ui.parse_log(log)
    assert result is None
    assert aks == "none"


# ── 2. modelUsage → 모델별 항목 ──────────────────────────────────────────────


def test_multi_model_usage_becomes_per_model_entries():
    evt = json.loads(
        _result_line(
            modelUsage={
                "claude-sonnet-5": {
                    "inputTokens": 2,
                    "outputTokens": 378,
                    "cacheReadInputTokens": 23972,
                    "cacheCreationInputTokens": 57608,
                },
                "claude-haiku-5": {
                    "inputTokens": 10,
                    "outputTokens": 20,
                    "cacheReadInputTokens": 5,
                    "cacheCreationInputTokens": 0,
                },
            }
        )
    )
    entries = ui.models_from_result(evt)
    by_model = {e["model"]: e for e in entries}
    assert set(by_model) == {"claude-sonnet-5", "claude-haiku-5"}
    s = by_model["claude-sonnet-5"]
    assert s["input_tokens"] == 2 and s["output_tokens"] == 378
    assert s["cache_read_input_tokens"] == 23972
    assert s["cache_creation_input_tokens"] == 57608
    h = by_model["claude-haiku-5"]
    assert h["input_tokens"] == 10 and h["output_tokens"] == 20


def test_no_model_usage_returns_empty_entries():
    """modelUsage 부재 → 빈 리스트. top-level usage 폴백을 하지 않는다(계획 M4).

    'unknown' 모델 쓰레기 행이 원장에 남지 않도록, run() 의 '모델 사용량 없음 — 스킵'
    경로가 처리하게 위임한다.
    """
    evt = {
        "type": "result",
        "session_id": "s",
        "model": "claude-sonnet-5",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_input_tokens": 7,
            "cache_creation_input_tokens": 3,
        },
    }
    assert ui.models_from_result(evt) == []


def test_main_skips_post_when_no_model_usage(monkeypatch, tmp_path):
    """modelUsage 없는 result → main() 은 0 을 반환하고 POST 를 호출하지 않는다."""
    log = tmp_path / "claude.log"
    log.write_text(
        _init_line("none")
        + "\n"
        + json.dumps({"type": "result", "session_id": "s", "usage": {"input_tokens": 1}})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")
    monkeypatch.setattr(
        ui, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("전송 금지"))
    )
    assert ui.main(["--log", str(log)]) == 0


# ── 3. key_source 유도 ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "aks,expected",
    [
        ("none", "subscription_seat"),
        (None, "subscription_seat"),
        ("ANTHROPIC_API_KEY", "org_api_key"),
        ("apiKeyHelper", "org_api_key"),
    ],
)
def test_key_source_derivation(aks, expected):
    assert ui._key_source(aks) == expected


# ── 4. payload 구성(env monkeypatch) ─────────────────────────────────────────


def test_build_payload_shape_with_env(monkeypatch):
    seat = str(uuid.uuid4())
    proj = str(uuid.uuid4())
    monkeypatch.setenv("CLICKEYE_SEAT_ID", seat)
    monkeypatch.setenv("CLICKEYE_PROJECT_ID", proj)
    evt = json.loads(_result_line())
    payload = ui.build_payload(
        evt, "none", request_kind="local_batch_implement", task_id="CE-328"
    )
    assert payload["session_id"] == "sess-abc"
    assert payload["request_kind"] == "local_batch_implement"
    assert payload["key_source"] == "subscription_seat"
    assert payload["seat_id"] == seat
    assert payload["project_id"] == proj
    assert payload["task_id"] == "CE-328"
    assert len(payload["models"]) == 1
    assert payload["meta"]["total_cost_usd"] == 0.35
    assert payload["meta"]["num_turns"] == 12
    assert payload["meta"]["api_key_source"] == "none"


def test_build_payload_drops_non_uuid_axes(monkeypatch):
    """비-UUID seat_id/project_id 는 None 으로 떨어뜨리되 사용량(models)은 유지한다."""
    monkeypatch.setenv("CLICKEYE_SEAT_ID", "not-a-uuid")
    monkeypatch.setenv("CLICKEYE_PROJECT_ID", "also-bad")
    evt = json.loads(_result_line())
    payload = ui.build_payload(
        evt, "none", request_kind="local_batch_implement", task_id="CE-328"
    )
    assert payload["seat_id"] is None
    assert payload["project_id"] is None
    assert payload["session_id"] == "sess-abc"
    assert len(payload["models"]) == 1  # 사용량은 살린다


def test_build_payload_null_axes_when_env_absent(monkeypatch):
    monkeypatch.delenv("CLICKEYE_SEAT_ID", raising=False)
    monkeypatch.delenv("CLICKEYE_PROJECT_ID", raising=False)
    evt = json.loads(_result_line())
    payload = ui.build_payload(evt, None, request_kind="local_batch_implement", task_id=None)
    assert payload["seat_id"] is None
    assert payload["project_id"] is None
    assert payload["task_id"] is None
    assert payload["key_source"] == "subscription_seat"  # 미확인 기본값


# ── 5. 베이스 URL 폴백 ───────────────────────────────────────────────────────


def test_base_url_fallback_order(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000/")
    monkeypatch.setenv("API_URL", "http://api:9000")
    # --api-url 최우선
    assert ui._base_url("http://arg:1234/") == "http://arg:1234"
    # 인자 없으면 FLOWOPS_GOVERNANCE_SERVICE_URL
    assert ui._base_url(None) == "http://gov:8000"
    monkeypatch.delenv("FLOWOPS_GOVERNANCE_SERVICE_URL", raising=False)
    assert ui._base_url(None) == "http://api:9000"
    monkeypatch.delenv("API_URL", raising=False)
    assert ui._base_url(None) is None


# ── 6. 전송(urlopen monkeypatch — 실제 네트워크 금지) ────────────────────────


class _FakeResp:
    def __init__(self, body=b'{"status":"recorded","rows":1}'):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_post_usage_sends_expected_request(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["data"] = req.data
        captured["headers"] = dict(req.header_items())
        captured["timeout"] = timeout
        return _FakeResp()

    monkeypatch.setattr(ui, "urlopen", fake_urlopen)
    payload = {"session_id": "s", "models": []}
    body = ui.post_usage(payload, "http://gov:8000", token="tok-123", timeout=5)
    assert "recorded" in body
    assert captured["url"] == "http://gov:8000/api/v1/llm/ingest/usage"
    assert captured["method"] == "POST"
    assert json.loads(captured["data"].decode()) == payload
    # 헤더 키는 정규화(Title-Case)됨
    hdr = {k.lower(): v for k, v in captured["headers"].items()}
    assert hdr.get("x-governance-token") == "tok-123"
    assert hdr.get("content-type") == "application/json"
    assert captured["timeout"] == 5


def test_main_exit_zero_on_send_failure(monkeypatch, tmp_path):
    log = tmp_path / "claude.log"
    log.write_text(_init_line("none") + "\n" + _result_line(), encoding="utf-8")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")

    def boom(req, timeout=None):
        raise OSError("네트워크 다운")

    monkeypatch.setattr(ui, "urlopen", boom)
    rc = ui.main(["--log", str(log), "--request-kind", "local_batch_implement"])
    assert rc == 0  # 전송 실패해도 파이프라인 불사


def test_main_exit_zero_when_no_result_event(monkeypatch, tmp_path):
    log = tmp_path / "claude.log"
    log.write_text("노이즈만 있는 로그\n", encoding="utf-8")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")
    # urlopen 이 호출되면 안 됨 — 호출 시 실패시켜 검증
    monkeypatch.setattr(
        ui, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("전송 금지"))
    )
    rc = ui.main(["--log", str(log)])
    assert rc == 0


def test_main_exit_zero_when_log_missing(monkeypatch):
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")
    rc = ui.main(["--log", "/nonexistent/path/claude.log"])
    assert rc == 0


def test_main_skips_post_when_no_session_id(monkeypatch, tmp_path):
    """result 에 session_id 가 없으면 확정 422 를 피하려 POST 를 보내지 않고 0 을 반환한다."""
    log = tmp_path / "claude.log"
    # session_id 없는 result(modelUsage 는 존재).
    result_no_session = json.dumps(
        {
            "type": "result",
            "modelUsage": {"claude-sonnet-5": {"inputTokens": 2, "outputTokens": 3}},
        }
    )
    log.write_text(_init_line("none") + "\n" + result_no_session + "\n", encoding="utf-8")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_SERVICE_URL", "http://gov:8000")
    monkeypatch.setattr(
        ui, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("전송 금지"))
    )
    assert ui.main(["--log", str(log)]) == 0


def test_main_exit_zero_on_argparse_error():
    """argparse 인자 오류(SystemExit)도 삼켜 파이프라인을 죽이지 않는다(exit 0)."""
    assert ui.main(["--bad-flag"]) == 0
    # --log 필수 인자 누락도 동일.
    assert ui.main([]) == 0
