from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_linear_credentials import UserLinearCredentials
from app.schemas.linear_credentials import LinearCredentialsSave, LinearCredentialsResponse

router = APIRouter(prefix="/me/linear-credentials", tags=["linear-credentials"])


async def _get_creds(
    user_id: UUID, db: AsyncSession
) -> UserLinearCredentials | None:
    result = await db.execute(
        select(UserLinearCredentials).where(UserLinearCredentials.user_id == user_id)
    )
    return result.scalar_one_or_none()


def _mask_api_key(encrypted: str) -> str:
    try:
        plain = decrypt(encrypted)
        return plain[:12] + "****"
    except Exception:
        return "****"


@router.post("/", response_model=LinearCredentialsResponse, status_code=status.HTTP_200_OK)
async def save_linear_credentials(
    data: LinearCredentialsSave,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinearCredentialsResponse:
    """Linear 자격증명 저장 (upsert). API 키는 Fernet 암호화. tunnel_url 제공 시 Linear webhook 자동 등록."""
    from app.core.crypto import decrypt as _decrypt
    from app.services.linear_service import ensure_webhook

    encrypted_key = encrypt(data.api_key)
    now = datetime.now(UTC)

    creds = await _get_creds(user.id, db)  # type: ignore[arg-type]
    if creds is None:
        creds = UserLinearCredentials(
            user_id=user.id,
            encrypted_api_key=encrypted_key,
            team_id=data.team_id,
            webhook_secret=data.webhook_secret,
            tunnel_url=data.tunnel_url,
        )
        db.add(creds)
    else:
        creds.encrypted_api_key = encrypted_key  # type: ignore[assignment]
        creds.team_id = data.team_id  # type: ignore[assignment]
        creds.webhook_secret = data.webhook_secret  # type: ignore[assignment]
        creds.tunnel_url = data.tunnel_url  # type: ignore[assignment]
        creds.updated_at = now  # type: ignore[assignment]

    await db.commit()
    await db.refresh(creds)

    # tunnel_url이 있으면 Linear webhook 자동 등록 (실패해도 자격증명 저장은 유지)
    if data.tunnel_url:
        try:
            webhook_url = f"{data.tunnel_url.rstrip('/')}/webhook/linear"
            wh_id = ensure_webhook(
                api_key=_decrypt(encrypted_key),
                team_id=data.team_id,
                url=webhook_url,
                secret=data.webhook_secret,
            )
            creds.linear_webhook_id = wh_id  # type: ignore[assignment]
            creds.updated_at = datetime.now(UTC)  # type: ignore[assignment]
            await db.commit()
            await db.refresh(creds)
        except Exception:
            pass  # webhook 등록 실패는 무시 (자격증명 저장은 성공)

    return LinearCredentialsResponse(
        api_key_masked=_mask_api_key(str(creds.encrypted_api_key)),
        team_id=str(creds.team_id),
        webhook_secret_set=creds.webhook_secret is not None,
        tunnel_url=creds.tunnel_url,
        linear_webhook_id=creds.linear_webhook_id,
        updated_at=creds.updated_at or now,
    )


@router.get("/", response_model=LinearCredentialsResponse)
async def get_linear_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinearCredentialsResponse:
    """저장된 Linear 자격증명 조회 (API 키는 마스킹)."""
    creds = await _get_creds(user.id, db)  # type: ignore[arg-type]
    if creds is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linear 자격증명이 없습니다")

    return LinearCredentialsResponse(
        api_key_masked=_mask_api_key(str(creds.encrypted_api_key)),
        team_id=str(creds.team_id),
        webhook_secret_set=creds.webhook_secret is not None,
        tunnel_url=creds.tunnel_url,
        linear_webhook_id=creds.linear_webhook_id,
        updated_at=creds.updated_at or creds.created_at,
    )


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_linear_credentials(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Linear 자격증명 삭제."""
    creds = await _get_creds(user.id, db)  # type: ignore[arg-type]
    if creds is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linear 자격증명이 없습니다")

    await db.delete(creds)
    await db.commit()
