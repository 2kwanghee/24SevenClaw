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

    return _check  # type: ignore[return-value]  # TODO: 타입 정합


SUPPORTED_LOCALES: tuple[str, ...] = ("ko", "en", "id", "ja")


def _locale_from_accept_language(request: Request) -> str | None:
    """Accept-Language 헤더에서 지원 언어 코드를 prefix 매칭한다. 없으면 None."""
    accept_lang = request.headers.get("Accept-Language", "").lower()
    for part in accept_lang.split(","):
        tag = part.split(";")[0].strip()
        for code in SUPPORTED_LOCALES:
            if tag.startswith(code):
                return code
    return None


def get_locale(
    request: Request,
    user: User | None = None,
    prefer_header: bool = False,
) -> Literal["ko", "en", "id", "ja"]:
    """사용자 locale을 결정한다.

    기본 우선순위:
    1. 인증 사용자의 user.language
    2. Accept-Language 헤더 (지원 언어 코드 prefix 매칭)
    3. fallback "en"

    prefer_header=True 이면 Accept-Language를 user.language보다 우선한다.
    위저드처럼 UI 언어 선택이 user.language에 동기화되지 않고 쿠키(→Accept-Language)로만
    전달되는 흐름에서 현재 선택 언어를 따르기 위해 사용한다.

    admin 엔드포인트에서는 이 함수를 사용하지 않고 "ko"를 직접 전달한다.
    """
    user_lang: str = (getattr(user, "language", "") or "") if user is not None else ""
    user_lang = user_lang if user_lang in SUPPORTED_LOCALES else ""

    if prefer_header:
        header_lang = _locale_from_accept_language(request)
        if header_lang:
            return header_lang  # type: ignore[return-value]
        if user_lang:
            return user_lang  # type: ignore[return-value]
        return "en"

    if user_lang:
        return user_lang  # type: ignore[return-value]
    header_lang = _locale_from_accept_language(request)
    if header_lang:
        return header_lang  # type: ignore[return-value]
    return "en"


async def require_superadmin(user: User = Depends(get_current_user)) -> User:
    """superadmin 전용 가드.

    admin 과 superadmin 은 ROLE_PERMISSIONS 를 다수 공유하므로 require_permission 을
    재사용할 수 없다. system_role == "superadmin" 을 명시적으로 검사한다.
    (rbac_service.py / ROLE_PERMISSIONS 는 미변경 — HIGH auth 경로 회피.)
    """
    role = getattr(user, "system_role", "") or ""
    if role != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="superadmin 권한이 필요합니다.",
        )
    return user


def require_ops_feature() -> None:
    """운영(Ops) 패널 feature flag 가드.

    `feature_ops_panel = False` 일 때 ops endpoint 가 모두 404 응답 (킬스위치).
    modernize 게이트와 동일 패턴 — 인증보다 먼저 평가되어 존재 자체를 은닉한다.
    """
    if not settings.feature_ops_panel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )


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
