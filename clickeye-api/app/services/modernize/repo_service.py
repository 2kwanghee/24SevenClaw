"""Modernize repo 캐시 서비스.

GitHub App installation token 으로 repo 목록을 조회하고, `github_repos` 테이블에
24h TTL 로 캐시한다. 사용자가 `?refresh=true` 로 호출하면 즉시 갱신.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.github_repo import GitHubRepo
from app.services import github_app_service

_CACHE_TTL = timedelta(hours=24)


async def list_repos(
    db: AsyncSession,
    *,
    installation_pk: UUID,
    installation_id: int,
    refresh: bool = False,
) -> list[GitHubRepo]:
    """installation 의 repo 목록 반환. 캐시 hit 시 DB 직접 반환, miss 시 GitHub 호출 + upsert.

    Args:
        db: async session
        installation_pk: GitHubInstallation.id (UUID PK)
        installation_id: GitHub 측 installation id (BigInt)
        refresh: True 면 캐시 무시하고 즉시 GitHub API 호출
    """
    if not refresh and not await _cache_stale(db, installation_pk):
        return await _fetch_from_db(db, installation_pk)

    # GitHub 에서 최신 목록 조회 + 캐시 갱신
    raw_repos = await github_app_service.list_installation_repos(installation_id)
    await _upsert_repos(db, installation_pk, raw_repos)
    return await _fetch_from_db(db, installation_pk)


async def _cache_stale(db: AsyncSession, installation_pk: UUID) -> bool:
    """24h TTL 기준으로 캐시 만료 여부. 캐시 행이 하나도 없으면 stale 로 간주."""
    result = await db.execute(
        select(GitHubRepo.cached_at)
        .where(GitHubRepo.installation_id == installation_pk)
        .order_by(GitHubRepo.cached_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return True
    # naive vs aware 처리: GitHubRepo.cached_at 은 timezone-aware 로 저장됨
    cached_at = row if row.tzinfo else row.replace(tzinfo=UTC)
    return datetime.now(UTC) - cached_at > _CACHE_TTL


async def _fetch_from_db(db: AsyncSession, installation_pk: UUID) -> list[GitHubRepo]:
    result = await db.execute(
        select(GitHubRepo)
        .where(GitHubRepo.installation_id == installation_pk)
        .order_by(GitHubRepo.pushed_at.desc().nulls_last(), GitHubRepo.full_name)
    )
    return list(result.scalars().all())


async def _upsert_repos(
    db: AsyncSession,
    installation_pk: UUID,
    raw_repos: list[dict[str, Any]],
) -> None:
    """GitHub API 응답을 github_repos 테이블에 upsert.

    같은 installation_id + gh_repo_id 가 이미 있으면 업데이트, 없으면 insert.
    이번 응답에 없는 기존 repo 는 그대로 둠 (사용자가 repo 접근 권한을 회수한 케이스
    는 M3 webhook 의 installation_repositories.removed 에서 처리 — MVP-2-A 단순화).
    """
    now = datetime.now(UTC)

    # 기존 repo 매핑
    result = await db.execute(
        select(GitHubRepo).where(GitHubRepo.installation_id == installation_pk)
    )
    existing: dict[int, GitHubRepo] = {
        int(cast(int, r.gh_repo_id)): r for r in result.scalars().all()
    }

    for raw in raw_repos:
        gh_id = raw.get("id")
        full_name = raw.get("full_name")
        if gh_id is None or not full_name:
            continue

        default_branch = raw.get("default_branch") or "main"
        private = bool(raw.get("private", True))
        language = raw.get("language")
        pushed_at_raw = raw.get("pushed_at")
        pushed_at: datetime | None = None
        if isinstance(pushed_at_raw, str):
            try:
                pushed_at = datetime.fromisoformat(pushed_at_raw.replace("Z", "+00:00"))
            except ValueError:
                pushed_at = None

        existing_row = existing.get(int(gh_id))
        if existing_row is None:
            row = GitHubRepo(
                installation_id=installation_pk,
                gh_repo_id=int(gh_id),
                full_name=full_name,
                default_branch=default_branch,
                private=private,
                language_primary=language,
                pushed_at=pushed_at,
                cached_at=now,
            )
            db.add(row)
        else:
            existing_row.full_name = full_name
            existing_row.default_branch = default_branch  # type: ignore[assignment]
            existing_row.private = private  # type: ignore[assignment]
            existing_row.language_primary = language  # type: ignore[assignment]
            existing_row.pushed_at = pushed_at  # type: ignore[assignment]
            existing_row.cached_at = now  # type: ignore[assignment]

    await db.commit()
