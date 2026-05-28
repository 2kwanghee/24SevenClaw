from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    OAuthLoginRequest,
    RefreshTokenRequest,
    RegisterResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    service = AuthService(db)
    return await service.register(data)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    service = AuthService(db)
    return await service.authenticate(data.email, data.password)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    return await service.refresh(data.refresh_token)


@router.post("/oauth", response_model=TokenResponse)
async def oauth_login(
    data: OAuthLoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """소셜 로그인 (GitHub/Google). 미가입 시 자동 회원가입."""
    service = AuthService(db)
    return await service.oauth_login(data)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """사용자 프로필을 업데이트한다 (display_name, language)."""
    if data.language is not None:
        if data.language not in ("ko", "en"):
            raise AppError.from_key("LANGUAGE_INVALID", locale="ko", status_code=400)
        user.language = data.language  # type: ignore[assignment]
    if data.display_name is not None:
        user.display_name = data.display_name  # type: ignore[assignment]
    user.updated_at = datetime.now(UTC)  # type: ignore[assignment]
    await db.commit()
    await db.refresh(user)
    return user
