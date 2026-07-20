"""GitHub App endpoints — install URL / OAuth callback / webhook 수신.

기존 OAuth login (`auth.py`) 흐름과 완전히 분리된 별개 prefix 사용.
모든 endpoint 는 `require_modernize_feature` 의존성으로 가드되어, feature flag OFF 시 404 응답.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_modernize_feature
from app.models.github_installation import GitHubInstallation
from app.models.user import User
from app.schemas.github_app import InstallUrlResponse
from app.services import github_app_service

router = APIRouter(
    prefix="/integrations/github/app",
    tags=["github-app"],
)

# state JWT 만료 — App 설치는 보통 30 초 ~ 수 분 소요
_STATE_JWT_EXPIRY_SECONDS = 10 * 60


def _service_unavailable_if_not_configured() -> None:
    if not github_app_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub App 이 아직 설정되지 않았습니다. 관리자에게 문의하세요.",
        )


def _encode_state(user_id: UUID) -> str:
    """CSRF state JWT 발급 — user_id 와 nonce 를 포함, 10분 만료."""
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + _STATE_JWT_EXPIRY_SECONDS,
        "purpose": "github_app_install",
    }
    return cast(str, jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm))


def _decode_state(state: str) -> UUID:
    """state JWT 검증 → user_id 반환. 실패 시 HTTPException."""
    try:
        payload = jwt.decode(
            state,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="설치 state 가 만료되었습니다. 다시 시도해 주세요.",
        ) from e
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="설치 state 가 유효하지 않습니다.",
        ) from e
    if payload.get("purpose") != "github_app_install":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="설치 state 가 유효하지 않습니다.",
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="설치 state 에 사용자 정보가 없습니다.",
        )
    return UUID(sub)


@router.get(
    "/install-url",
    response_model=InstallUrlResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def get_install_url(
    user: User = Depends(get_current_user),
) -> InstallUrlResponse:
    """GitHub App 설치 URL + CSRF state JWT 발급.

    프론트엔드는 `install_url?state=<state>` 로 사용자를 redirect 한다.
    GitHub UI 에서 설치 완료 후 ClickEye 의 `/callback` 으로 돌아오며,
    state 가 callback 단계에서 검증된다.
    """
    _service_unavailable_if_not_configured()
    return InstallUrlResponse(
        install_url=github_app_service.build_install_url(),
        state=_encode_state(user.id),  # type: ignore[arg-type]
    )


@router.get(
    "/callback",
    dependencies=[Depends(require_modernize_feature)],
)
async def github_app_callback(
    installation_id: int,
    state: str,
    setup_action: str | None = None,
    code: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """GitHub App 설치 완료 후 redirect 수신.

    1. state JWT 검증 → 어떤 사용자 인지 확인
    2. App JWT 로 installation 메타 조회 → installation 의 account 정보 확보
    3. (선택) user-to-server OAuth code 가 있으면 교환해 사용자 검증 추가
    4. github_installations 테이블 upsert
    5. frontend 의 modernize/connected 페이지로 302 redirect
    """
    _service_unavailable_if_not_configured()
    user_id = _decode_state(state)

    # 설치 메타 조회 (App JWT 사용)
    try:
        meta = await github_app_service.fetch_installation_meta(installation_id)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub installation 메타 조회 실패: {e}",
        ) from e

    account = meta.get("account") or {}
    account_login = account.get("login") or ""
    account_type = account.get("type") or "User"
    target_type = meta.get("target_type")
    permissions = meta.get("permissions") or {}
    repository_selection = meta.get("repository_selection") or "selected"
    suspended_at_raw = meta.get("suspended_at")

    # upsert github_installations
    result = await db.execute(
        select(GitHubInstallation).where(GitHubInstallation.installation_id == installation_id)
    )
    inst = result.scalar_one_or_none()

    now = datetime.now(UTC)
    if inst is None:
        inst = GitHubInstallation(
            user_id=user_id,
            installation_id=installation_id,
            account_login=account_login,
            account_type=account_type,
            target_type=target_type,
            permissions=permissions,
            repository_selection=repository_selection,
            installed_at=now,
        )
        db.add(inst)
    else:
        # 기존 installation 재설치 또는 권한 변경
        inst.user_id = user_id  # type: ignore[assignment]
        inst.account_login = account_login  # type: ignore[assignment]
        inst.account_type = account_type  # type: ignore[assignment]
        inst.target_type = target_type  # type: ignore[assignment]
        inst.permissions = permissions  # type: ignore[assignment]
        inst.repository_selection = repository_selection  # type: ignore[assignment]
        inst.revoked_at = None  # type: ignore[assignment]
        if suspended_at_raw:
            try:
                inst.suspended_at = datetime.fromisoformat(  # type: ignore[assignment]
                    suspended_at_raw.replace("Z", "+00:00")
                )
            except ValueError:
                inst.suspended_at = None  # type: ignore[assignment]
        else:
            inst.suspended_at = None  # type: ignore[assignment]

    await db.commit()
    await db.refresh(inst)

    # 프론트엔드로 302 redirect (M4 에서 connected 페이지 구현 예정)
    redirect_url = (
        f"{settings.frontend_url.rstrip('/')}"
        f"/solutions/modernize/connected?installation_id={installation_id}"
    )
    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": redirect_url},
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_modernize_feature)],
)
async def github_app_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """GitHub App webhook 수신.

    처리 이벤트:
      - installation (created/deleted/suspend/unsuspend)
      - installation_repositories (added/removed) — MVP-2-A 에서는 캐시 무효화 정도만
    """
    _service_unavailable_if_not_configured()

    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not github_app_service.verify_webhook_signature(payload, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="webhook 서명이 유효하지 않습니다.",
        )

    try:
        body = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="webhook payload JSON 파싱 실패.",
        ) from e

    event_type = request.headers.get("X-GitHub-Event", "")
    action = body.get("action", "")
    installation = body.get("installation") or {}
    installation_id = installation.get("id")

    if event_type == "installation" and installation_id is not None:
        await _handle_installation_event(
            db,
            action=action,
            installation_id=int(installation_id),
        )
    # installation_repositories 등 다른 이벤트는 M4 의 repo 캐시에서 처리.

    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _handle_installation_event(
    db: AsyncSession,
    *,
    action: str,
    installation_id: int,
) -> None:
    """installation 이벤트 처리 — DB 상태 갱신."""
    result = await db.execute(
        select(GitHubInstallation).where(GitHubInstallation.installation_id == installation_id)
    )
    inst = result.scalar_one_or_none()
    if inst is None:
        # 아직 callback 으로 등록 안 된 경우 — webhook 만 먼저 도착 가능. 무시.
        return

    now = datetime.now(UTC)
    if action == "deleted":
        inst.revoked_at = now  # type: ignore[assignment]
    elif action == "suspend":
        inst.suspended_at = now  # type: ignore[assignment]
    elif action == "unsuspend":
        inst.suspended_at = None  # type: ignore[assignment]
    # 다른 action 은 무시.

    await db.commit()
