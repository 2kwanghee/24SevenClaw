"""Modernize endpoints — installations / repos 조회.

Feature flag `feature_modernize_enabled` OFF 시 모든 endpoint 404.
사용자 소유 installation 만 접근 가능 (installations.user_id == current.id).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime  # noqa: TC003 — runtime cast 에 필요
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_modernize_feature
from app.models.codebase_analysis import CodebaseAnalysis
from app.models.github_installation import GitHubInstallation
from app.models.github_repo import GitHubRepo
from app.models.modernize_phase_artifact import ModernizePhaseArtifact
from app.models.modernize_recommendation import ModernizeRecommendation
from app.models.modernize_session import ModernizeSession
from app.models.user import User
from app.schemas.modernize import (
    CodebaseAnalysisResponse,
    FinalizeRequest,
    FinalizeResponse,
    InstallationListItem,
    ModernizePhaseArtifactResponse,
    ModernizeRecommendationResponse,
    ModernizeRecommendationUpdate,
    ModernizeSessionCreate,
    ModernizeSessionResponse,
    PreflightApproveRequest,
    RepoListItem,
)
from app.services.modernize import finalize as finalize_svc
from app.services.modernize import pipeline, repo_service, zip_builder
from app.services.modernize import preflight as preflight_svc

_ALLOWED_SCENARIOS = frozenset({"versionup", "refactor", "language_migrate"})
_PREFLIGHT_ARTIFACT_TYPE = "preflight_review"

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


# ----------------------------------------------------------------------
# Pre-flight 게이트 (Phase 5)
# ----------------------------------------------------------------------


async def _get_latest_preflight_artifact(
    db: AsyncSession, session_id: UUID
) -> ModernizePhaseArtifact | None:
    result = await db.execute(
        select(ModernizePhaseArtifact)
        .where(
            ModernizePhaseArtifact.session_id == session_id,
            ModernizePhaseArtifact.phase == "preflight",
            ModernizePhaseArtifact.artifact_type == _PREFLIGHT_ARTIFACT_TYPE,
        )
        .order_by(ModernizePhaseArtifact.created_at.desc())
    )
    return result.scalars().first()


async def _selected_recommendation_payloads(
    db: AsyncSession, session_id: UUID
) -> list[dict[str, Any]]:
    rec_result = await db.execute(
        select(ModernizeRecommendation)
        .where(
            ModernizeRecommendation.session_id == session_id,
            ModernizeRecommendation.selected.is_(True),
        )
        .order_by(ModernizeRecommendation.priority.asc())
    )
    return [
        {
            "title": r.title,
            "category": r.category,
            "target_path": r.target_path,
            "before": r.before,
            "after": r.after,
            "risk": r.risk,
            "rationale_md": r.rationale_md,
            "prompt_md": r.prompt_md,
        }
        for r in rec_result.scalars().all()
    ]


@router.post(
    "/sessions/{session_id}/preflight",
    response_model=ModernizePhaseArtifactResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def generate_preflight_review(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModernizePhaseArtifactResponse:
    """선택된 권장안 + as-is 스캔 신호로 Pre-flight 체크리스트를 (재)생성한다.

    재생성 시 기존 승인은 무효화된다(계획이 바뀌었으므로 재검토 필요).
    """
    session_row, _ = await _get_recommendation_with_ownership(db, user, session_id, rec_id=None)

    rec_payloads = await _selected_recommendation_payloads(db, session_id)

    analysis_result = await db.execute(
        select(CodebaseAnalysis).where(CodebaseAnalysis.session_id == session_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    framework_signals: dict[str, Any] = (
        cast("dict[str, Any] | None", analysis.framework_signals) if analysis is not None else None
    ) or {}

    content = preflight_svc.build_preflight_checklist(
        recommendations=rec_payloads, framework_signals=framework_signals
    )
    content_md = preflight_svc.render_markdown(content)

    artifact = await _get_latest_preflight_artifact(db, session_id)
    if artifact is None:
        artifact = ModernizePhaseArtifact(
            session_id=session_id,
            phase="preflight",
            artifact_type=_PREFLIGHT_ARTIFACT_TYPE,
        )
        db.add(artifact)

    artifact.content_json = content  # type: ignore[assignment]
    artifact.content_md = content_md  # type: ignore[assignment]
    artifact.approved_at = None  # type: ignore[assignment]
    session_row.current_phase = "preflight"  # type: ignore[assignment]

    await db.commit()
    await db.refresh(artifact)
    return ModernizePhaseArtifactResponse.model_validate(artifact)


@router.get(
    "/sessions/{session_id}/preflight",
    response_model=ModernizePhaseArtifactResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def get_preflight_review(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModernizePhaseArtifactResponse:
    """가장 최근 Pre-flight 체크리스트 조회."""
    await _get_recommendation_with_ownership(db, user, session_id, rec_id=None)
    artifact = await _get_latest_preflight_artifact(db, session_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pre-flight 사전검토가 아직 생성되지 않았습니다.",
        )
    return ModernizePhaseArtifactResponse.model_validate(artifact)


@router.post(
    "/sessions/{session_id}/preflight/approve",
    response_model=ModernizePhaseArtifactResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def approve_preflight_review(
    session_id: UUID,
    body: PreflightApproveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModernizePhaseArtifactResponse:
    """Pre-flight 체크리스트 승인. block 항목이 남아 있으면 409.

    HIGH 리스크 작업 block 항목은 `ack_high_risk=True` 로 수동 확인 후 예외적으로 승인 가능.
    승인 후에만 실행 팩(ZIP) 다운로드가 허용된다.
    """
    session_row, _ = await _get_recommendation_with_ownership(db, user, session_id, rec_id=None)
    artifact = await _get_latest_preflight_artifact(db, session_id)
    if artifact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="먼저 Pre-flight 사전검토를 생성하세요.",
        )

    content = dict(cast("dict[str, Any]", artifact.content_json) or {})
    can_approve, reason = preflight_svc.evaluate_approval(content, ack_high_risk=body.ack_high_risk)
    if not can_approve:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)

    content["acknowledged_high_risk"] = body.ack_high_risk
    artifact.content_json = content  # type: ignore[assignment]
    artifact.content_md = preflight_svc.render_markdown(content)  # type: ignore[assignment]
    artifact.approved_at = datetime.now(UTC)  # type: ignore[assignment]
    session_row.current_phase = "execute"  # type: ignore[assignment]

    await db.commit()
    await db.refresh(artifact)
    return ModernizePhaseArtifactResponse.model_validate(artifact)


# ----------------------------------------------------------------------
# Finalize + ZIP download (M7)
# ----------------------------------------------------------------------


from fastapi.responses import StreamingResponse  # noqa: E402 — endpoint-only import


@router.post(
    "/sessions/{session_id}/finalize",
    response_model=FinalizeResponse,
    dependencies=[Depends(require_modernize_feature)],
)
async def finalize_session(
    session_id: UUID,
    body: FinalizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinalizeResponse:
    """Linear 이슈 일괄 등록 + ZIP URL 응답 + 세션 상태 'finalized'."""
    # 세션 + 소유 검증
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
    if str(session_row.status) not in ("ready", "finalized"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"세션이 finalize 가능한 상태가 아닙니다. (status={session_row.status})",
        )

    # selected=true 권장안
    rec_result = await db.execute(
        select(ModernizeRecommendation)
        .where(
            ModernizeRecommendation.session_id == session_id,
            ModernizeRecommendation.selected.is_(True),
        )
        .order_by(ModernizeRecommendation.priority.asc())
    )
    selected_recs = list(rec_result.scalars().all())

    # Linear 등록 (옵션)
    linear_result = {
        "parent_url": "",
        "parent_identifier": "",
        "child_count": 0,
        "errors": [],
    }
    if body.create_linear_issues and selected_recs:
        creds = await finalize_svc.resolve_linear_credentials(
            db, cast(UUID, user.id), project_id=body.project_id
        )
        if creds is not None:
            api_key, team_id = creds
            # CodebaseAnalysis 조회
            analysis_result = await db.execute(
                select(CodebaseAnalysis).where(CodebaseAnalysis.session_id == session_id)
            )
            analysis = analysis_result.scalar_one_or_none()
            linear_result = await finalize_svc.register_linear_issues(
                db,
                session_row=session_row,
                analysis=analysis,
                selected_recs=selected_recs,
                api_key=api_key,
                team_id=team_id,
            )

    # 세션 상태 finalized
    await finalize_svc.mark_finalized(db, session_id)

    return FinalizeResponse(
        session_id=session_id,
        status="finalized",
        linear_parent_url=linear_result["parent_url"] or None,
        linear_parent_identifier=linear_result["parent_identifier"] or None,
        linear_child_count=cast(int, linear_result["child_count"]),
        linear_errors=linear_result["errors"],
        zip_url=f"/api/v1/modernize/sessions/{session_id}/zip",
        selected_recommendation_count=len(selected_recs),
    )


@router.get(
    "/sessions/{session_id}/zip",
    dependencies=[Depends(require_modernize_feature)],
)
async def download_zip(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Modernize ZIP 다운로드. finalize 후 또는 ready 상태에서 호출 가능."""
    # 소유 검증
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

    # Pre-flight 게이트 — 승인 없이는 실행 팩(ZIP) 발급 불가
    preflight_artifact = await _get_latest_preflight_artifact(db, session_id)
    if preflight_artifact is None or preflight_artifact.approved_at is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Pre-flight 사전검토 승인이 필요합니다. "
                "POST /preflight 로 체크리스트를 생성하고 /preflight/approve 로 승인하세요."
            ),
        )

    # 분석 + 권장안 조회
    analysis_result = await db.execute(
        select(CodebaseAnalysis).where(CodebaseAnalysis.session_id == session_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석이 완료되지 않았습니다.",
        )

    rec_result = await db.execute(
        select(ModernizeRecommendation)
        .where(
            ModernizeRecommendation.session_id == session_id,
            ModernizeRecommendation.selected.is_(True),
        )
        .order_by(ModernizeRecommendation.priority.asc())
    )
    recs = list(rec_result.scalars().all())

    analysis_data = {
        "loc_total": analysis.loc_total,
        "file_count": analysis.file_count,
        "lang_distribution": analysis.lang_distribution,
        "manifests": analysis.manifests,
        "outdated_packages": analysis.outdated_packages,
        "framework_signals": analysis.framework_signals,
        "risk_flags": analysis.risk_flags,
        "tokens_used": analysis.tokens_used,
    }

    rec_payloads = [
        {
            "id": str(rec.id),
            "linear_identifier": rec.linear_identifier,
            "title": rec.title,
            "rationale_md": rec.rationale_md,
            "prompt_md": rec.prompt_md,
            "target_path": rec.target_path,
            "risk": rec.risk,
            "effort": rec.effort,
            "category": rec.category,
        }
        for rec in recs
    ]
    linear_issues = [
        {
            "rec_id": str(rec.id),
            "linear_issue_id": rec.linear_issue_id,
            "linear_identifier": rec.linear_identifier,
            "title": rec.title,
        }
        for rec in recs
        if rec.linear_identifier
    ]

    zip_bytes = zip_builder.generate_modernize_zip(
        repo_full_name=str(session_row.repo_full_name),
        scenario=str(session_row.scenario),
        session_id=str(session_id),
        llm_summary_md=cast("str | None", analysis.llm_summary_md),
        analysis_data=analysis_data,
        recommendations=rec_payloads,
        linear_issues=linear_issues,
        preflight_review_md=cast("str | None", preflight_artifact.content_md),
    )

    safe_name = str(session_row.repo_full_name).replace("/", "_")
    filename = f"modernize_{safe_name}_{session_id}.zip"

    return StreamingResponse(
        iter([zip_bytes]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
