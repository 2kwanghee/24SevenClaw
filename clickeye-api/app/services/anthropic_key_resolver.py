"""사용자 Anthropic API 키 / OAuth Setup Token 해석 헬퍼."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.models.user_anthropic_credentials import UserAnthropicCredentials


async def resolve_user_anthropic_key(
    user_id: UUID,
    db: AsyncSession,
    credential_type: str = "api_key",
) -> str | None:
    """사용자가 등록한 자격증명을 복호화해서 반환. 미등록이거나 복호화 실패 시 None."""
    result = await db.execute(
        select(UserAnthropicCredentials).where(
            UserAnthropicCredentials.user_id == user_id,
            UserAnthropicCredentials.credential_type == credential_type,
        )
    )
    creds = result.scalar_one_or_none()
    if creds is None:
        return None
    try:
        return decrypt(str(creds.encrypted_api_key))
    except Exception:
        return None


async def resolve_user_oauth_setup_token(
    user_id: UUID,
    db: AsyncSession,
) -> str | None:
    """사용자가 등록한 OAuth Setup Token 반환. 미등록 시 None."""
    return await resolve_user_anthropic_key(user_id, db, credential_type="oauth_setup_token")
