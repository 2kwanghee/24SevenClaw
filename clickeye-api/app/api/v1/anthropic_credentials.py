"""사용자 Anthropic API 키 / OAuth Setup Token 저장/조회/삭제 엔드포인트."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials
from app.schemas.anthropic_credentials import AnthropicCredentialsResponse, AnthropicCredentialsSave

router = APIRouter(prefix="/me/anthropic-credentials", tags=["anthropic-credentials"])


async def _get_creds(
    user_id: UUID, db: AsyncSession, credential_type: str = "api_key"
) -> UserAnthropicCredentials | None:
    result = await db.execute(
        select(UserAnthropicCredentials).where(
            UserAnthropicCredentials.user_id == user_id,
            UserAnthropicCredentials.credential_type == credential_type,
        )
    )
    return result.scalar_one_or_none()


def _mask_key(encrypted: str) -> str:
    try:
        plain = decrypt(encrypted)
        return plain[:16] + "****"
    except Exception:
        return "****"


@router.post("/", response_model=AnthropicCredentialsResponse, status_code=status.HTTP_200_OK)
async def save_anthropic_credentials(
    data: AnthropicCredentialsSave,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnthropicCredentialsResponse:
    """Anthropic API 키 또는 OAuth Setup Token 저장 (upsert). Fernet 암호화 후 DB 저장."""
    if not data.api_key.startswith("sk-ant-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 Anthropic API 키 형식이 아닙니다 (sk-ant-... 로 시작해야 합니다).",
        )

    encrypted_key = encrypt(data.api_key)
    now = datetime.now(UTC)

    creds = await _get_creds(user.id, db, credential_type=data.credential_type)  # type: ignore[arg-type]
    if creds is None:
        creds = UserAnthropicCredentials(
            user_id=user.id,
            credential_type=data.credential_type,
            encrypted_api_key=encrypted_key,
        )
        db.add(creds)
    else:
        creds.encrypted_api_key = encrypted_key  # type: ignore[assignment]
        creds.updated_at = now  # type: ignore[assignment]

    await db.commit()
    await db.refresh(creds)

    return AnthropicCredentialsResponse(
        api_key_masked=_mask_key(str(creds.encrypted_api_key)),
        credential_type=data.credential_type,
        updated_at=creds.updated_at or now,
    )


@router.get("/", response_model=AnthropicCredentialsResponse)
async def get_anthropic_credentials(
    credential_type: str = Query(default="api_key", description="조회할 자격증명 유형"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnthropicCredentialsResponse:
    """저장된 Anthropic 자격증명 조회 (마스킹)."""
    creds = await _get_creds(user.id, db, credential_type=credential_type)  # type: ignore[arg-type]
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="저장된 자격증명이 없습니다.",
        )

    return AnthropicCredentialsResponse(
        api_key_masked=_mask_key(str(creds.encrypted_api_key)),
        credential_type=credential_type,
        updated_at=creds.updated_at or creds.created_at,
    )


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_anthropic_credentials(
    credential_type: str = Query(default="api_key", description="삭제할 자격증명 유형"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """저장된 Anthropic 자격증명 삭제."""
    creds = await _get_creds(user.id, db, credential_type=credential_type)  # type: ignore[arg-type]
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="저장된 자격증명이 없습니다.",
        )

    await db.delete(creds)
    await db.commit()
