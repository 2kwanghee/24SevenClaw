"""사용자 Anthropic API 키 / OAuth Setup Token 저장/조회/삭제 엔드포인트."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.core.exceptions import AppError
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials
from app.schemas.anthropic_credentials import AnthropicCredentialsResponse, AnthropicCredentialsSave
from app.schemas.seat import SeatRegisterRequest, SeatResponse
from app.services.seat_service import SeatService

router = APIRouter(prefix="/me/anthropic-credentials", tags=["anthropic-credentials"])


def _seat_response(seat: UserAnthropicCredentials) -> SeatResponse:
    """시트 응답 조립 — 토큰(평문/마스킹)은 어떤 경우에도 담지 않는다."""
    return SeatResponse(
        seat_id=seat.id,
        seat_status=str(seat.seat_status),
        created_at=seat.created_at or datetime.now(UTC),
        updated_at=seat.updated_at,
    )


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
        # 메시지는 중앙 예외 핸들러에서 요청 locale로 재해석된다.
        raise AppError.from_key(
            "ANTHROPIC_KEY_INVALID_FORMAT",
            status_code=status.HTTP_400_BAD_REQUEST,
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
        raise AppError.from_key(
            "CREDENTIALS_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return AnthropicCredentialsResponse(
        api_key_masked=_mask_key(str(creds.encrypted_api_key)),
        credential_type=credential_type,
        updated_at=creds.updated_at or creds.created_at,
    )


@router.put("/seat", response_model=SeatResponse, status_code=status.HTTP_200_OK)
async def register_seat(
    data: SeatRegisterRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SeatResponse:
    """본인 구독 시트 등록/교체 (다프로젝트화 P4).

    평문 OAuth 토큰(`claude setup-token` 산출물)을 수신해 Fernet 암호화 저장하고
    상태를 active 로 초기화한다. 응답에 토큰은 포함되지 않는다.
    사용자당 시트 1개(본인 계정) — 재호출은 교체다.
    """
    seat = await SeatService(db).register(user.id, data.oauth_token)  # type: ignore[arg-type]
    return _seat_response(seat)


@router.get("/seat", response_model=SeatResponse)
async def get_seat(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SeatResponse:
    """본인 구독 시트 상태 조회 (토큰 미노출). 미등록이면 404."""
    seat = await SeatService(db).get_seat_or_404(user.id)  # type: ignore[arg-type]
    return _seat_response(seat)


@router.delete("/seat", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seat(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """본인 구독 시트 해제. 미등록이면 404."""
    await SeatService(db).delete(user.id)  # type: ignore[arg-type]


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_anthropic_credentials(
    credential_type: str = Query(default="api_key", description="삭제할 자격증명 유형"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """저장된 Anthropic 자격증명 삭제."""
    creds = await _get_creds(user.id, db, credential_type=credential_type)  # type: ignore[arg-type]
    if creds is None:
        raise AppError.from_key(
            "CREDENTIALS_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    await db.delete(creds)
    await db.commit()
