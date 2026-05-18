"""GitHub App 인프라 — JWT 발급, installation token, webhook 서명 검증, OAuth code 교환.

ClickEye Modernize 의 repo-connect 단계에서 사용된다. 모든 GitHub API 호출은 두 단계 인증을 거친다:
  1. App private key 로 RS256 JWT 서명 (10 분 만료)
  2. JWT 로 `/app/installations/{id}/access_tokens` 호출 → 1 시간짜리 installation token
     이후 repo API 호출은 이 installation token 으로.

사용자 식별 (user-to-server) 은 OAuth `code` 를 user token 으로 교환해 그 user 의 github_id 가
ClickEye 의 user 와 일치하는지 검증.

Settings 가 비어있으면 `is_configured()` 가 False — 호출자는 503 처리.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any, cast

import httpx
from jose import jwt

from app.config import settings

# JWT 만료 — GitHub 권장 최대 10분
_JWT_EXPIRY_SECONDS = 9 * 60
# 시계 오차 보정 — iat 을 60 초 과거로 설정 (GitHub 권장)
_JWT_IAT_OFFSET = -60

_GITHUB_API_BASE = "https://api.github.com"
_GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_API = f"{_GITHUB_API_BASE}/user"


def is_configured() -> bool:
    """GitHub App 관련 6 settings 가 모두 설정되어 있는지 확인.

    하나라도 비어있으면 endpoint 는 503 응답해야 한다.
    """
    return all(
        [
            settings.github_app_id > 0,
            settings.github_app_private_key.strip(),
            settings.github_app_client_id.strip(),
            settings.github_app_client_secret.strip(),
            settings.github_app_webhook_secret.strip(),
            settings.github_app_slug.strip(),
        ]
    )


def create_app_jwt() -> str:
    """RS256 으로 App JWT 발급. GitHub API `/app/*` 엔드포인트 호출용.

    Raises:
        RuntimeError: GitHub App 미설정 시
    """
    if not is_configured():
        raise RuntimeError("GitHub App is not configured. Set GITHUB_APP_* env vars.")

    now = int(time.time())
    payload = {
        "iat": now + _JWT_IAT_OFFSET,
        "exp": now + _JWT_EXPIRY_SECONDS,
        "iss": settings.github_app_id,
    }
    # python-jose 는 PEM 문자열을 직접 받아 RS256 서명 가능
    return cast(
        str,
        jwt.encode(payload, settings.github_app_private_key, algorithm="RS256"),
    )


def verify_webhook_signature(payload: bytes, signature_header: str | None) -> bool:
    """GitHub webhook 의 X-Hub-Signature-256 검증.

    signature_header: 'sha256=<hex>' 형식. None 또는 형식 불일치 시 False.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    if not settings.github_app_webhook_secret:
        return False

    expected = hmac.new(
        settings.github_app_webhook_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


async def get_installation_token(installation_id: int) -> dict[str, Any]:
    """`POST /app/installations/{id}/access_tokens` 호출. 1 시간짜리 installation token 발급.

    Returns:
        {"token": "...", "expires_at": "...", "permissions": {...}, "repository_selection": "..."}

    Raises:
        RuntimeError: 설정 미완료 또는 GitHub API 에러
    """
    app_jwt = create_app_jwt()
    url = f"{_GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    if res.status_code != 201:
        raise RuntimeError(
            f"GitHub installation token 발급 실패 (status={res.status_code}): {res.text[:300]}"
        )
    return cast(dict[str, Any], res.json())


async def fetch_installation_meta(installation_id: int) -> dict[str, Any]:
    """`GET /app/installations/{id}` 로 installation 상세 메타 조회.

    callback 단계에서 사용자가 정말 해당 installation 의 소유자인지 교차 검증.
    """
    app_jwt = create_app_jwt()
    url = f"{_GITHUB_API_BASE}/app/installations/{installation_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            url,
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    if res.status_code != 200:
        raise RuntimeError(
            f"GitHub installation 조회 실패 (status={res.status_code}): {res.text[:300]}"
        )
    return cast(dict[str, Any], res.json())


async def exchange_user_oauth_code(code: str) -> dict[str, Any]:
    """user-to-server OAuth code → user access token 교환.

    Returns:
        {"access_token": "...", "token_type": "bearer", "scope": "..."}
    """
    if not is_configured():
        raise RuntimeError("GitHub App is not configured.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.post(
            _GITHUB_OAUTH_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_app_client_id,
                "client_secret": settings.github_app_client_secret,
                "code": code,
            },
        )
    if res.status_code != 200:
        raise RuntimeError(
            f"GitHub OAuth code 교환 실패 (status={res.status_code}): {res.text[:300]}"
        )
    body = cast(dict[str, Any], res.json())
    if "access_token" not in body:
        raise RuntimeError(f"GitHub OAuth 응답에 access_token 없음: {body}")
    return body


async def fetch_user_with_token(user_access_token: str) -> dict[str, Any]:
    """user access token 으로 `/user` 호출 → GitHub user 메타.

    callback 에서 사용자 식별 검증용.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(
            _GITHUB_USER_API,
            headers={
                "Authorization": f"Bearer {user_access_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
    if res.status_code != 200:
        raise RuntimeError(f"GitHub user 조회 실패 (status={res.status_code}): {res.text[:300]}")
    return cast(dict[str, Any], res.json())


def build_install_url() -> str:
    """GitHub App 설치 페이지 URL. 사용자가 클릭하면 GitHub UI 가 설치 흐름을 진행.

    설치 완료 후 GitHub 가 App 의 setup_url (= ClickEye callback) 으로 redirect.
    """
    if not settings.github_app_slug:
        raise RuntimeError("GITHUB_APP_SLUG is not configured.")
    return f"https://github.com/apps/{settings.github_app_slug}/installations/new"
