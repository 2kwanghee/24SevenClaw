"""Modernize endpoints — installations / repos 조회.

Feature flag `feature_modernize_enabled` OFF 시 모든 endpoint 404.
사용자 소유 installation 만 접근 가능 (installations.user_id == current.id).
"""

from __future__ import annotations

import asyncio
from datetime import datetime  # noqa: TC003 — runtime cast 에 필요
from typing import cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_modernize_feature
from app.models.codebase_analysis import CodebaseAnalysis
from app.models.github_installation import GitHubInstallation
from app.models.github_repo import GitHubRepo
from app.models.modernize_recommendation import ModernizeRecommendation
from app.models.modernize_session import ModernizeSession
from app.models.user import User
from app.schemas.modernize import (
    CodebaseAnalysisResponse,
    InstallationListItem,
    ModernizeRecommendationResponse,
    ModernizeRecommendationUpdate,
    ModernizeSessionCreate,
    ModernizeSessionResponse,
    RepoListItem,
)
from app.services.modernize import pipeline, repo_service

_ALLOWED_SCENARIOS = frozenset({"versionup", "refactor", "language_migrate"})

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


# ----------------------------------------------------------------------
# ModernizeSession — 분석 세션 생성/조회/결과
# ----------------------------------------------------------------------


@router.post(
    "/sessions",
    response_model=ModernizeSessionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_modernize_feature)],
)
async def create_session(
    body: ModernizeSessionCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModernizeSessionResponse:
    """ModernizeSession 생성 + 백그라운드 7-step pipeline 시작."""
    if body.scenario not in _ALLOWED_SCENARIOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"scenario 는 {sorted(_ALLOWED_SCENARIOS)} 중 하나여야 합니다.",
        )

    # 소유 검증 — installation 이 현재 사용자 것이어야
    result = await db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.id == body.installation_pk,
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

    # pipeline 이 사용할 수 있도록 GitHub 측 installation_id 를 extra 에 저장
    extra = {"github_installation_id": int(cast(int, inst.installation_id))}

    session_row = ModernizeSession(
        user_id=user.id,
        organization_id=user.organization_id,
        installation_id=cast(UUID, inst.id),
        repo_full_name=body.repo_full_name,
        repo_branch=body.branch,
        scenario=body.scenario,
        goals_text=body.goals_text,
        target_stack=body.target_stack,
        status="pending",
        progress_pct=0,
        extra=extra,
    )
    db.add(session_row)
    await db.commit()
    await db.refresh(session_row)

    # 백그라운드 pipeline 시작 — BackgroundTasks 는 response 반환 후 실행됨
    session_id = cast(UUID, session_row.id)

    async def _runner() -> None:
        await pipeline.run_pipeline(session_id)

    background_tasks.add_task(asyncio.create_task, _runner())

    return ModernizeSessionResponse.model_validate(session_row)


@router.get(
    "/sessions/{session_id}",
    response_model=ModernizeSessionResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModernizeSessionResponse:
    """세션 상태 + 진행률 폴링."""
    result = await db.execute(
        select(ModernizeSession).where(
            ModernizeSession.id == session_id,
            ModernizeSession.user_id == user.id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ModernizeSession 을 찾을 수 없습니다.",
        )
    return ModernizeSessionResponse.model_validate(row)


@router.get(
    "/sessions/{session_id}/analysis",
    response_model=CodebaseAnalysisResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def get_session_analysis(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CodebaseAnalysisResponse:
    """분석 완료 후 코드베이스 분석 결과 조회. 미완료 시 404."""
    # 소유 검증 + 세션 조회
    session_result = await db.execute(
        select(ModernizeSession).where(
            ModernizeSession.id == session_id,
            ModernizeSession.user_id == user.id,
        )
    )
    session_row = session_result.scalar_one_or_none()
    if session_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ModernizeSession 을 찾을 수 없습니다.",
        )

    analysis_result = await db.execute(
        select(CodebaseAnalysis).where(CodebaseAnalysis.session_id == session_id)
    )
    analysis_row = analysis_result.scalar_one_or_none()
    if analysis_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석이 아직 완료되지 않았습니다.",
        )

    return CodebaseAnalysisResponse.model_validate(analysis_row)


# ----------------------------------------------------------------------
# ModernizeRecommendation — 권장안 조회/편집 (M6)
# ----------------------------------------------------------------------


async def _get_recommendation_with_ownership(
    db: AsyncSession,
    user: User,
    session_id: UUID,
    rec_id: UUID | None = None,
) -> tuple[ModernizeSession, ModernizeRecommendation | None]:
    """세션 소유 검증 + (옵션) 권장안 조회."""
    session_result = await db.execute(
        select(ModernizeSession).where(
            ModernizeSession.id == session_id,
            ModernizeSession.user_id == user.id,
        )
    )
    session_row = session_result.scalar_one_or_none()
    if session_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ModernizeSession 을 찾을 수 없습니다.",
        )
    if rec_id is None:
        return session_row, None

    rec_result = await db.execute(
        select(ModernizeRecommendation).where(
            ModernizeRecommendation.id == rec_id,
            ModernizeRecommendation.session_id == session_id,
        )
    )
    rec_row = rec_result.scalar_one_or_none()
    if rec_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="권장안을 찾을 수 없습니다.",
        )
    return session_row, rec_row


@router.get(
    "/sessions/{session_id}/recommendations",
    response_model=list[ModernizeRecommendationResponse],
    dependencies=[Depends(require_modernize_feature)],
)
async def list_recommendations(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ModernizeRecommendationResponse]:
    """세션의 권장안 목록. priority asc 정렬."""
    await _get_recommendation_with_ownership(db, user, session_id, rec_id=None)
    result = await db.execute(
        select(ModernizeRecommendation)
        .where(ModernizeRecommendation.session_id == session_id)
        .order_by(
            ModernizeRecommendation.priority.asc(),
            ModernizeRecommendation.idx.asc(),
        )
    )
    rows = list(result.scalars().all())
    return [ModernizeRecommendationResponse.model_validate(r) for r in rows]


@router.patch(
    "/sessions/{session_id}/recommendations/{rec_id}",
    response_model=ModernizeRecommendationResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def update_recommendation(
    session_id: UUID,
    rec_id: UUID,
    body: ModernizeRecommendationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModernizeRecommendationResponse:
    """권장안 편집 — selected / priority / prompt_md 만 변경 가능."""
    _, rec_row = await _get_recommendation_with_ownership(db, user, session_id, rec_id)
    assert rec_row is not None  # noqa: S101 — helper invariant

    changed = False
    if body.selected is not None:
        rec_row.selected = body.selected  # type: ignore[assignment]
        changed = True
    if body.priority is not None:
        rec_row.priority = body.priority  # type: ignore[assignment]
        changed = True
    if body.prompt_md is not None:
        rec_row.prompt_md = body.prompt_md  # type: ignore[assignment]
        changed = True

    if changed:
        await db.commit()
        await db.refresh(rec_row)
    return ModernizeRecommendationResponse.model_validate(rec_row)
