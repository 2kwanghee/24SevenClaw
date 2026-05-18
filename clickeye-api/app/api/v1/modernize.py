"""Modernize endpoints — installations / repos 조회.

Feature flag `feature_modernize_enabled` OFF 시 모든 endpoint 404.
사용자 소유 installation 만 접근 가능 (installations.user_id == current.id).
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — runtime cast 에 필요
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_modernize_feature
from app.models.github_installation import GitHubInstallation
from app.models.github_repo import GitHubRepo
from app.models.user import User
from app.schemas.modernize import InstallationListItem, RepoListItem
from app.services.modernize import repo_service

router = APIRouter(
    prefix="/modernize",
    tags=["modernize"],
)


@router.get(
    "/installations",
    response_model=list[InstallationListItem],
    dependencies=[Depends(require_modernize_feature)],
)
async def list_installations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[InstallationListItem]:
    """현재 사용자에 매핑된 GitHub App installation 목록.

    revoked_at IS NULL 인 활성 installation 만 반환. 각 항목에 repo_count 포함.
    """
    # 활성 installation
    result = await db.execute(
        select(GitHubInstallation)
        .where(
            GitHubInstallation.user_id == user.id,
            GitHubInstallation.revoked_at.is_(None),
        )
        .order_by(GitHubInstallation.installed_at.desc())
    )
    installations = list(result.scalars().all())
    if not installations:
        return []

    # repo_count 일괄 조회
    inst_ids = [inst.id for inst in installations]
    count_rows = await db.execute(
        select(GitHubRepo.installation_id, func.count(GitHubRepo.id))
        .where(GitHubRepo.installation_id.in_(inst_ids))
        .group_by(GitHubRepo.installation_id)
    )
    count_map: dict[UUID, int] = {row[0]: int(row[1]) for row in count_rows.fetchall()}

    return [
        InstallationListItem(
            id=cast(UUID, inst.id),
            installation_id=int(cast(int, inst.installation_id)),
            account_login=str(inst.account_login),
            account_type=str(inst.account_type),
            repository_selection=str(inst.repository_selection),
            installed_at=cast("datetime", inst.installed_at),
            suspended_at=cast("datetime | None", inst.suspended_at),
            repo_count=count_map.get(cast(UUID, inst.id), 0),
        )
        for inst in installations
    ]


@router.get(
    "/installations/{installation_pk}/repos",
    response_model=list[RepoListItem],
    dependencies=[Depends(require_modernize_feature)],
)
async def list_installation_repos(
    installation_pk: UUID,
    refresh: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RepoListItem]:
    """특정 installation 의 repo 목록 (24h 캐시).

    Args:
        installation_pk: GitHubInstallation.id (UUID PK)
        refresh: True 면 캐시 무시하고 GitHub API 호출

    Returns:
        repo 목록. 캐시 hit 시 DB 직접 반환.

    Raises:
        404: installation 이 존재하지 않거나 사용자 소유 아님
        503: GitHub App 미설정 (refresh=True 인 경우)
    """
    # 소유 검증
    result = await db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.id == installation_pk,
            GitHubInstallation.user_id == user.id,
            GitHubInstallation.revoked_at.is_(None),
        )
    )
    inst = result.scalar_one_or_none()
    if inst is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Installation 을 찾을 수 없거나 접근 권한이 없습니다.",
        )

    try:
        repos = await repo_service.list_repos(
            db,
            installation_pk=cast(UUID, inst.id),
            installation_id=int(cast(int, inst.installation_id)),
            refresh=refresh,
        )
    except RuntimeError as e:
        # GitHub App 미설정 또는 GitHub API 에러
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"GitHub repo 목록 조회 실패: {e}",
        ) from e

    return [
        RepoListItem(
            gh_repo_id=int(cast(int, r.gh_repo_id)),
            full_name=str(r.full_name),
            default_branch=str(r.default_branch),
            private=bool(r.private),
            language_primary=cast("str | None", r.language_primary),
            pushed_at=cast("datetime | None", r.pushed_at),
        )
        for r in repos
    ]
