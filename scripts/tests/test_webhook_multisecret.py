"""webhook_server 다중 signing secret 검증 테스트.

프로젝트마다 Linear 워크스페이스가 다르면 signing secret 도 갈린다. 수신부는 무 DB
원칙이라 어느 워크스페이스가 보냈는지 조회할 수 없으므로, 후보 시크릿 전부와 대조해
하나라도 맞으면 통과시킨다.

커버:
  - 2번째 시크릿으로 서명된 요청 통과 (핵심 신규 동작)
  - 어느 후보와도 안 맞는 서명 거부
  - 단일 WEBHOOK_SECRET 만 설정된 환경 회귀 0 (목록 길이 1, 검증 동일)
  - load_env 병합: env 우선 / .env 폴백 / 공백·빈 항목 제거 / 중복 제거

Usage:
    cd ClickEye && pytest scripts/tests/test_webhook_multisecret.py -v
"""

from __future__ import annotations

import hashlib
import hmac
import os
import sys

import pytest

# scripts/ 를 import path 에 추가(webhook_server import 용).
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import webhook_server as ws  # noqa: E402

PAYLOAD = b'{"action":"update","type":"Issue"}'
SECRET_A = "secret-workspace-a"
SECRET_B = "secret-workspace-b"
SECRET_C = "secret-workspace-c"


def _sign(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_second_secret_passes():
    """목록의 2번째 시크릿으로 서명해도 통과 — 프로젝트별 워크스페이스 대응 핵심."""
    sig = _sign(PAYLOAD, SECRET_B)
    assert ws.verify_signature_any(PAYLOAD, sig, [SECRET_A, SECRET_B, SECRET_C]) is True


def test_unknown_secret_rejected():
    """후보 어디에도 없는 시크릿으로 서명하면 거부."""
    sig = _sign(PAYLOAD, "secret-not-registered")
    assert ws.verify_signature_any(PAYLOAD, sig, [SECRET_A, SECRET_B]) is False


def test_tampered_payload_rejected():
    """서명은 유효한 시크릿이라도 본문이 변조되면 거부."""
    sig = _sign(PAYLOAD, SECRET_A)
    assert ws.verify_signature_any(b'{"action":"evil"}', sig, [SECRET_A, SECRET_B]) is False


def test_single_secret_regression():
    """단일 시크릿 목록은 기존 verify_signature 와 동일하게 동작."""
    sig = _sign(PAYLOAD, SECRET_A)
    assert ws.verify_signature(PAYLOAD, sig, SECRET_A) is True
    assert ws.verify_signature_any(PAYLOAD, sig, [SECRET_A]) is True
    assert ws.verify_signature_any(PAYLOAD, _sign(PAYLOAD, SECRET_B), [SECRET_A]) is False


def test_empty_secret_list_matches_nothing():
    """목록이 비면 어떤 서명도 통과하지 못한다(기동 거부의 fail-closed 전제)."""
    assert ws.verify_signature_any(PAYLOAD, _sign(PAYLOAD, SECRET_A), []) is False


def test_split_secrets_trims_and_drops_empty():
    assert ws._split_secrets(" a , b ,, c ,") == ["a", "b", "c"]
    assert ws._split_secrets("") == []


@pytest.fixture
def env_isolated(monkeypatch, tmp_path):
    """load_env 를 격리 실행 — env 변수와 PROJECT_DIR(.env 탐색 경로)를 모두 대체."""
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRETS", raising=False)
    monkeypatch.setattr(ws, "PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(ws, "WEBHOOK_SECRET", None)
    monkeypatch.setattr(ws, "WEBHOOK_SECRETS", [])
    return tmp_path


def test_load_env_single_only_regression(monkeypatch, env_isolated):
    """WEBHOOK_SECRET 하나만 설정된 기존 환경 — 목록 길이 1, 기존 전역도 그대로 채워진다."""
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET_A)
    ws.load_env()
    assert ws.WEBHOOK_SECRET == SECRET_A
    assert ws.WEBHOOK_SECRETS == [SECRET_A]


def test_load_env_merges_single_and_multi(monkeypatch, env_isolated):
    """단일 + 목록이 함께 설정되면 병합하되 중복은 한 번만 남는다."""
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET_A)
    monkeypatch.setenv("WEBHOOK_SECRETS", f" {SECRET_B} , {SECRET_A} ,, {SECRET_C} ")
    ws.load_env()
    assert ws.WEBHOOK_SECRETS == [SECRET_A, SECRET_B, SECRET_C]


def test_load_env_multi_only(monkeypatch, env_isolated):
    """WEBHOOK_SECRETS 만 설정돼도 검증이 활성화된다."""
    monkeypatch.setenv("WEBHOOK_SECRETS", f"{SECRET_B},{SECRET_C}")
    ws.load_env()
    assert ws.WEBHOOK_SECRET is None
    assert ws.WEBHOOK_SECRETS == [SECRET_B, SECRET_C]


def test_load_env_dotenv_fallback(env_isolated):
    """env 가 비면 .env 에서 두 키 모두 읽는다."""
    (env_isolated / ".env").write_text(
        f"WEBHOOK_SECRET={SECRET_A}\nWEBHOOK_SECRETS={SECRET_B},{SECRET_C}\n",
        encoding="utf-8",
    )
    ws.load_env()
    assert ws.WEBHOOK_SECRETS == [SECRET_A, SECRET_B, SECRET_C]


def test_load_env_prefers_env_over_dotenv(monkeypatch, env_isolated):
    """env 로 온 값이 .env 값을 덮는다(기존 우선순위 유지)."""
    (env_isolated / ".env").write_text("WEBHOOK_SECRET=from-dotenv\n", encoding="utf-8")
    monkeypatch.setenv("WEBHOOK_SECRET", SECRET_A)
    ws.load_env()
    assert ws.WEBHOOK_SECRETS == [SECRET_A]


def test_load_env_none_configured(env_isolated):
    """아무것도 없으면 빈 목록 — 수신전용 모드는 이 상태에서 기동을 거부한다."""
    ws.load_env()
    assert ws.WEBHOOK_SECRET is None
    assert ws.WEBHOOK_SECRETS == []
