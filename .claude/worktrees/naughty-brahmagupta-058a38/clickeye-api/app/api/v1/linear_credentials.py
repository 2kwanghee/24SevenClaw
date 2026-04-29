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
from app.schemas.linear_credentials import LinearConnectionStatus, LinearCredentialsSave, LinearCredentialsResponse

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
    """Linear 자격증명 저장 (upsert). API 키는 Fernet 암호화. tunnel_url 제공 시 Linear webhook 자동 등록.
    api_key 미입력 시 기존 키 유지 (tunnel_url·webhook_secret만 갱신 가능).
    """
    from app.core.crypto import decrypt as _decrypt
    from app.services.linear_service import ensure_webhook

    now = datetime.now(UTC)

    creds = await _get_creds(user.id, db)  # type: ignore[arg-type]

    # API 키 처리: 신규 api_key가 있으면 암호화, 없으면 기존 키 유지
    if data.api_key is not None:
        encrypted_key = encrypt(data.api_key)
    elif creds is not None:
        encrypted_key = str(creds.encrypted_api_key)  # 기존 키 유지
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="신규 등록 시 api_key가 필요합니다.",
        )

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


@router.get("/status", response_model=LinearConnectionStatus)
async def get_linear_connection_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LinearConnectionStatus:
    """Linear 연동 준비 상태 조회 — 자격증명/webhook/tunnel 가용성 한 번에 확인."""
    import asyncio
    from urllib.error import URLError
    from urllib.request import Request, urlopen

    from app.core.crypto import decrypt as _decrypt
    from app.services.linear_service import _TEAM_QUERY, _call

    creds = await _get_creds(user.id, db)  # type: ignore[arg-type]
    if creds is None:
        return LinearConnectionStatus(
            credentials_saved=False,
            webhook_registered=False,
            tunnel_url=None,
            tunnel_reachable=None,
            team_name=None,
        )

    # tunnel 응답 확인 (5초 타임아웃, 동기 → 스레드)
    tunnel_reachable: bool | None = None
    if creds.tunnel_url:
        def _check_tunnel(url: str) -> bool:
            try:
                req = Request(f"{url.rstrip('/')}/health", method="HEAD")
                with urlopen(req, timeout=5):
                    return True
            except (URLError, OSError, Exception):
                return False

        tunnel_reachable = await asyncio.to_thread(_check_tunnel, str(creds.tunnel_url))

    # Linear 팀 이름 조회 (실패해도 None 반환)
    team_name: str | None = None
    try:
        api_key = _decrypt(str(creds.encrypted_api_key))
        data = await asyncio.to_thread(_call, api_key, _TEAM_QUERY, {"id": str(creds.team_id)})
        team = data.get("team") or {}
        team_name = team.get("name") or None
    except Exception:
        pass

    return LinearConnectionStatus(
        credentials_saved=True,
        webhook_registered=bool(creds.linear_webhook_id),
        tunnel_url=creds.tunnel_url,
        tunnel_reachable=tunnel_reachable,
        team_name=team_name,
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
