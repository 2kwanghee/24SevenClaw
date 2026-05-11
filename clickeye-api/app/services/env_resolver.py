"""서버에 저장된 사용자 자격증명으로 ZIP env_vars를 채우는 헬퍼."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt
from app.models.project_linear_credentials import ProjectLinearCredentials
from app.models.user_linear_credentials import UserLinearCredentials
from app.services.anthropic_key_resolver import resolve_user_anthropic_key


async def resolve_linear_key(
    user_id: UUID, project_id: UUID | None, db: AsyncSession
) -> str | None:
    """Linear API 키를 반환. project-level 우선, user-level 폴백."""
    if project_id:
        result = await db.execute(
            select(ProjectLinearCredentials).where(
                ProjectLinearCredentials.project_id == project_id
            )
        )
        creds = result.scalar_one_or_none()
        if creds is not None:
            try:
                return decrypt(str(creds.encrypted_api_key))
            except Exception:
                pass

    result = await db.execute(
        select(UserLinearCredentials).where(
            UserLinearCredentials.user_id == user_id
        )
    )
    creds = result.scalar_one_or_none()
    if creds is None:
        return None
    try:
        return decrypt(str(creds.encrypted_api_key))
    except Exception:
        return None


async def resolve_linear_team_id(
    user_id: UUID, project_id: UUID | None, db: AsyncSession
) -> str | None:
    """Linear 팀 ID를 반환. project-level 우선, user-level 폴백."""
    if project_id:
        result = await db.execute(
            select(ProjectLinearCredentials).where(
                ProjectLinearCredentials.project_id == project_id
            )
        )
        creds = result.scalar_one_or_none()
        if creds is not None and creds.team_id:
            return str(creds.team_id)

    result = await db.execute(
        select(UserLinearCredentials).where(
            UserLinearCredentials.user_id == user_id
        )
    )
    creds = result.scalar_one_or_none()
    if creds is None:
        return None
    return str(creds.team_id) if creds.team_id else None


async def merge_saved_credentials_into_env(
    *,
    user_id: UUID,
    project_id: UUID | None,
    db: AsyncSession,
    env_vars: dict[str, str],
    auth_method: str = "api_key",
) -> dict[str, str]:
    """env_vars에 비어있는 항목을 서버에 저장된 사용자 자격증명으로 채운다.

    auth_method에 따라 Anthropic 자격증명 채움 방식이 달라진다:
    - api_key:       ANTHROPIC_API_KEY 자동 채움
    - oauth_browser: Anthropic 자격증명 채움 완전 스킵 (.env에 키 잔존 방지)

    사용자가 명시적으로 입력한 값이 있으면 항상 그 값을 우선한다.
    Linear 자동 채움은 인증 모드와 무관하게 동일하게 동작한다.
    """
    out = dict(env_vars or {})

    if auth_method == "api_key":
        if not out.get("ANTHROPIC_API_KEY", "").strip():
            anthropic_key = await resolve_user_anthropic_key(user_id, db)
            if anthropic_key:
                out["ANTHROPIC_API_KEY"] = anthropic_key
    elif auth_method == "oauth_browser":
        # ANTHROPIC_API_KEY는 절대 채우지 않음
        out.pop("ANTHROPIC_API_KEY", None)

    if not out.get("LINEAR_API_KEY", "").strip():
        linear_key = await resolve_linear_key(user_id, project_id, db)
        if linear_key:
            out["LINEAR_API_KEY"] = linear_key

    if not out.get("LINEAR_TEAM_ID", "").strip():
        linear_team_id = await resolve_linear_team_id(user_id, project_id, db)
        if linear_team_id:
            out["LINEAR_TEAM_ID"] = linear_team_id

    return out
