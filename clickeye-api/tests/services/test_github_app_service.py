"""GitHub App service 단위 테스트 — JWT 생성, 서명 검증, is_configured.

실제 GitHub API 호출은 없음 (M3 의 사용자 측 App 등록 후 통합 테스트는 별개).
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterator

import pytest
from jose import jwt as jose_jwt

from app.config import settings
from app.services import github_app_service

# ----- 픽스처: settings 임시 패치 -----------------------------------------

# 테스트용 PEM RSA private key (1024-bit). 실서비스 키는 절대 사용하지 않는다.
_TEST_PEM = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQDdlatRjRjogo3WojgGHFHYLugdUWAY9iR3fy4arWNA1KoS8kVw33cJibXr8bvwUAUparCwlvdbH6dvEOfou0/gCFQsHUfQrSDv+MuSUMAe8jzKE4qW+jK+xQU9a03GUnKHkkle+Q0pX/g6jXZ7r1ODOlmAS8AXxqM8XAcsi6PgjJzlNGN3VQ0nrgkkZf8N9N6jHTBjlBfYNn5fb6m1Y4cpFD5jH0FvgT9HVOprtBoiPpOuibPaG4nGZdRJ4xmlT3F9wIDAQABAoGAdGzm9F0kQfgnoFwLmOI9YcGRsiBxK3yvFmM+Z6kSjVf7uoeuJjeu0CzPC4eRBxqL+L7TKlEUe3oVcGZB5UTAd+TM5pYClUUTeFwUGTMCV+TVO1qXgGTtkmgrwwq+szJvWX6IsRDxKMqL1ydhEK+v9KhJUx2BFLp9YBzKB0PR2HUCQQD8B9ofKUE2nb7tFw5cBQNz4ldzNRkdHrugw/aWmkD8eyZ7lrFA4VEvVi8wlYjOpsJojxnSQI/dD/uHVCNc7gI/AkEA4Q1MnlpfL/dx9wEikG+UMz5Q0F7krOZjCEsKbZkbXdGmcBHbA1nP+rrhcUf0Q0Th2vrSXNVe4PsxXqGT5pIs6QJBAOyOC79RBJL2WeQrCnGMrupgVjsaTUlGI4FA1srntPnzMtsBOLpEDb1ZWzHM4Plbij3I05+oyobX7l5j2tQdSjUCQAyLgQ74Wo+1lN6QcUmKFW2/xMOaFp8c1zR4FOBfBn4mAcZpvjvJzhk1bvevG7K2BVPiy00uMnXTowoG2fnnzpkCQGYpHDpCSdpDe9HXfRX4SglMlVQELiJzXxc5dpgZ1Aytg+TXNVxQOMxiNDQVy81/cBzAxRZX2qpDx2unFsXl1nU=
-----END RSA PRIVATE KEY-----"""


@pytest.fixture
def configured_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """GitHub App settings 를 테스트용 값으로 임시 설정."""
    monkeypatch.setattr(settings, "github_app_id", 12345)
    monkeypatch.setattr(settings, "github_app_private_key", _TEST_PEM)
    monkeypatch.setattr(settings, "github_app_client_id", "Iv1.test_client_id")
    monkeypatch.setattr(settings, "github_app_client_secret", "test_client_secret")
    monkeypatch.setattr(settings, "github_app_webhook_secret", "test_webhook_secret")
    monkeypatch.setattr(settings, "github_app_slug", "clickeye-modernize-test")
    yield


@pytest.fixture
def unconfigured_app(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """GitHub App settings 를 비어있는 상태로."""
    monkeypatch.setattr(settings, "github_app_id", 0)
    monkeypatch.setattr(settings, "github_app_private_key", "")
    monkeypatch.setattr(settings, "github_app_client_id", "")
    monkeypatch.setattr(settings, "github_app_client_secret", "")
    monkeypatch.setattr(settings, "github_app_webhook_secret", "")
    monkeypatch.setattr(settings, "github_app_slug", "")
    yield


# ----- is_configured ------------------------------------------------------


def test_is_configured_true_when_all_settings_present(configured_app: None) -> None:
    assert github_app_service.is_configured() is True


def test_is_configured_false_when_all_empty(unconfigured_app: None) -> None:
    assert github_app_service.is_configured() is False


def test_is_configured_false_when_one_field_missing(
    monkeypatch: pytest.MonkeyPatch, configured_app: None
) -> None:
    # private key 만 빈 값으로
    monkeypatch.setattr(settings, "github_app_private_key", "")
    assert github_app_service.is_configured() is False


def test_is_configured_false_when_app_id_zero(
    monkeypatch: pytest.MonkeyPatch, configured_app: None
) -> None:
    monkeypatch.setattr(settings, "github_app_id", 0)
    assert github_app_service.is_configured() is False


# ----- create_app_jwt -----------------------------------------------------


def test_create_app_jwt_returns_signed_token(configured_app: None) -> None:
    token = github_app_service.create_app_jwt()
    # RS256 JWT 형식: header.payload.signature
    parts = token.split(".")
    assert len(parts) == 3

    # 공개키 없이 RS256 검증을 위해 unverified decode 로 payload 만 확인
    payload = jose_jwt.get_unverified_claims(token)
    assert payload["iss"] == 12345
    assert "iat" in payload
    assert "exp" in payload
    assert payload["exp"] - payload["iat"] <= 11 * 60  # ≤ 11 분


def test_create_app_jwt_raises_when_not_configured(unconfigured_app: None) -> None:
    with pytest.raises(RuntimeError, match="not configured"):
        github_app_service.create_app_jwt()


# ----- verify_webhook_signature -------------------------------------------


def test_verify_webhook_signature_valid(configured_app: None) -> None:
    payload = b'{"action":"installation","installation":{"id":1}}'
    expected_sig = hmac.new(b"test_webhook_secret", payload, hashlib.sha256).hexdigest()
    header = f"sha256={expected_sig}"
    assert github_app_service.verify_webhook_signature(payload, header) is True


def test_verify_webhook_signature_invalid(configured_app: None) -> None:
    payload = b'{"action":"installation"}'
    bad_header = "sha256=" + ("0" * 64)
    assert github_app_service.verify_webhook_signature(payload, bad_header) is False


def test_verify_webhook_signature_missing_header(configured_app: None) -> None:
    payload = b'{"a":1}'
    assert github_app_service.verify_webhook_signature(payload, None) is False
    assert github_app_service.verify_webhook_signature(payload, "") is False


def test_verify_webhook_signature_wrong_prefix(configured_app: None) -> None:
    payload = b'{"a":1}'
    expected = hmac.new(b"test_webhook_secret", payload, hashlib.sha256).hexdigest()
    # sha1= 로 시작 → 거부
    assert github_app_service.verify_webhook_signature(payload, f"sha1={expected}") is False


def test_verify_webhook_signature_no_secret(unconfigured_app: None) -> None:
    payload = b'{"a":1}'
    # secret 미설정 → 항상 False
    assert github_app_service.verify_webhook_signature(payload, "sha256=anything") is False


# ----- build_install_url --------------------------------------------------


def test_build_install_url(configured_app: None) -> None:
    url = github_app_service.build_install_url()
    assert url == "https://github.com/apps/clickeye-modernize-test/installations/new"


def test_build_install_url_raises_when_slug_missing(
    monkeypatch: pytest.MonkeyPatch, configured_app: None
) -> None:
    monkeypatch.setattr(settings, "github_app_slug", "")
    with pytest.raises(RuntimeError, match="GITHUB_APP_SLUG"):
        github_app_service.build_install_url()
