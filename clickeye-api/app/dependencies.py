from collections.abc import Callable
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User
from app.services.rbac_service import ROLE_PERMISSIONS

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인 세션(액세스 토큰)이 만료되었습니다. 다시 로그인해 주세요.",
        ) from e
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다. 다시 로그인해 주세요.",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰에 사용자 정보가 없습니다. 다시 로그인해 주세요.",
        )

    user = await db.get(User, UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
        )

    return user


def require_permission(permission: str) -> Callable[..., User]:
    """권한 검증 의존성 팩토리. 사용자의 시스템 역할로 권한 확인."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        role = getattr(user, "system_role", "member") or "member"
        permissions = ROLE_PERMISSIONS.get(role, [])
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"권한이 부족합니다: {permission}",
            )
        return user

    return _check


def get_locale(
    request: Request,
    user: User | None = None,
) -> Literal["ko", "en"]:
    """사용자 locale을 결정한다.

    우선순위:
    1. 인증 사용자의 user.language
    2. Accept-Language 헤더 ("ko" 포함 시 "ko")
    3. fallback "en"

    admin 엔드포인트에서는 이 함수를 사용하지 않고 "ko"를 직접 전달한다.
    """
    if user is not None:
        lang: str = getattr(user, "language", "") or ""
        if lang == "ko":
            return "ko"
        if lang == "en":
            return "en"
    accept_lang = request.headers.get("Accept-Language", "")
    if "ko" in accept_lang.lower():
        return "ko"
    return "en"


def require_modernize_feature() -> None:
    """ClickEye Modernize feature flag 가드.

    `feature_modernize_enabled = False` 일 때 신규 endpoint 가 모두 404 응답.
    기존 사용자에게 베타 기능이 노출되지 않도록 보장 (비침습성 원칙).
    """
    if not settings.feature_modernize_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )
