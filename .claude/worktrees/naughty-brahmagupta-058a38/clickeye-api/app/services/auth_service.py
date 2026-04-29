from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import OAuthLoginRequest, TokenResponse, UserCreate


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, data: UserCreate) -> User:
        # 이메일 중복 확인
        stmt = select(User).where(User.email == data.email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise AppError("EMAIL_EXISTS", "이미 등록된 이메일입니다", 409)

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            display_name=data.display_name,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> TokenResponse:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None or not verify_password(password, str(user.password_hash)):
            raise AppError("INVALID_CREDENTIALS", "이메일 또는 비밀번호가 올바르지 않습니다", 401)

        if not user.is_active:
            raise AppError("USER_INACTIVE", "비활성화된 계정입니다", 403)

        return self._create_tokens(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_refresh_token(refresh_token)
        if payload is None:
            raise AppError("INVALID_TOKEN", "유효하지 않은 리프레시 토큰입니다", 401)

        user_id = payload.get("sub")
        user = await self.db.get(User, UUID(user_id))
        if user is None or not user.is_active:
            raise AppError("USER_NOT_FOUND", "사용자를 찾을 수 없습니다", 401)

        return self._create_tokens(user)

    async def oauth_login(self, data: OAuthLoginRequest) -> TokenResponse:
        """소셜 로그인: 기존 사용자면 토큰 발급, 없으면 자동 가입 후 발급."""
        # oauth_provider + oauth_id로 기존 사용자 검색
        stmt = select(User).where(
            User.oauth_provider == data.provider,
            User.oauth_id == data.oauth_id,
        )
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            # 동일 이메일로 가입된 계정이 있는지 확인
            stmt = select(User).where(User.email == data.email)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()

            if user is not None:
                # 기존 이메일 계정에 OAuth 연결
                user.oauth_provider = data.provider  # type: ignore[assignment]
                user.oauth_id = data.oauth_id  # type: ignore[assignment]
                if data.avatar_url and not user.avatar_url:
                    user.avatar_url = data.avatar_url  # type: ignore[assignment]
            else:
                # 신규 사용자 자동 가입
                user = User(
                    email=data.email,
                    display_name=data.display_name,
                    avatar_url=data.avatar_url,
                    oauth_provider=data.provider,
                    oauth_id=data.oauth_id,
                )
                self.db.add(user)

            await self.db.commit()
            await self.db.refresh(user)

        if not user.is_active:
            raise AppError("USER_INACTIVE", "비활성화된 계정입니다", 403)

        return self._create_tokens(user)

    @staticmethod
    def _create_tokens(user: User) -> TokenResponse:
        token_data = {"sub": str(user.id)}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
