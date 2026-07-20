"""부트스트랩 setup_token 발급/검증 서비스."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

_SCOPE = "setup"


@dataclass
class SetupTokenClaims:
    project_id: UUID
    user_id: UUID


def issue(project_id: UUID, user_id: UUID) -> tuple[str, str]:
    """setup_token JWT를 발급하고 (token, sha256_hash) 쌍을 반환한다."""
    expire = datetime.now(UTC) + timedelta(days=settings.setup_token_expire_days)
    payload: dict[str, Any] = {
        "pid": str(project_id),
        "uid": str(user_id),
        "scope": _SCOPE,
        "exp": expire,
    }
    token: str = cast(
        str,
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm),
    )
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def verify(token: str, stored_hash: str | None) -> SetupTokenClaims | None:
    """토큰 서명·만료·스코프·해시를 검증하고 클레임을 반환한다.

    검증 실패 시 None 반환.
    """
    if stored_hash is None:
        return None
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None
    if payload.get("scope") != _SCOPE:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    if token_hash != stored_hash:
        return None
    try:
        return SetupTokenClaims(
            project_id=UUID(str(payload["pid"])),
            user_id=UUID(str(payload["uid"])),
        )
    except (KeyError, ValueError):
        return None


async def issue_for_project(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
) -> str:
    """프로젝트에 신규 setup_token을 발급하고 DB에 해시를 저장한다."""
    from sqlalchemy import update

    from app.models.project import Project

    token, token_hash = issue(project_id, user_id)
    await db.execute(
        update(Project).where(Project.id == project_id).values(setup_token_hash=token_hash)
    )
    await db.commit()
    return token
