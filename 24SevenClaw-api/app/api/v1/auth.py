from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    OAuthLoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
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
