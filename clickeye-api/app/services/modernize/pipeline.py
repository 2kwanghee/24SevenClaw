"""7-step pipeline orchestrator.

`POST /modernize/sessions` 가 BackgroundTask 로 호출. 각 단계 사이에 진행률을 DB 에 업데이트.
워크스페이스는 Step 7 (cleanup) 에서 항상 삭제 — 예외 발생 시에도.

진행률 % (단계별):
  Step 1 clone        0 → 15
  Step 2 scan        15 → 35
  Step 3 manifest    35 → 55
  Step 4 outdated    55 → 70
  Step 5 sample      70 → 80
  Step 6 LLM summary 80 → 95
  Step 7 cleanup     95 → 100
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.codebase_analysis import CodebaseAnalysis
from app.models.modernize_recommendation import ModernizeRecommendation
from app.models.modernize_session import ModernizeSession
from app.services.modernize import (
    clone,
    llm_summary,
    manifest,
    outdated,
    sample,
    scan,
)
from app.services.modernize import (
    recommendations as recommendations_svc,
)

logger = logging.getLogger(__name__)


async def run_pipeline(session_id: UUID) -> None:
    """ModernizeSession 1 건의 분석을 끝까지 수행.

    BackgroundTask 로 호출되므로 request session 과 분리된 새 async_session 을 연다.
    예외는 status='failed' + error JSON 으로 기록 후 swallowed.
    """
    async with async_session() as db:
        session_row = await _load_session(db, session_id)
        if session_row is None:
            logger.warning("ModernizeSession %s not found", session_id)
            return

        try:
            await _execute(db, session_row)
        except Exception as e:
            logger.exception("Modernize pipeline failed for session %s", session_id)
            await _mark_failed(db, session_id, error_message=str(e))
        finally:
            # 항상 워크스페이스 정리 — 시크릿/코드 비보관 원칙
            clone.cleanup_workspace(session_id)


async def _execute(db: AsyncSession, session_row: ModernizeSession) -> None:
    session_id: UUID = session_row.id  # type: ignore[assignment]

    # Step 1 clone
    await _update_status(db, session_id, status="cloning", progress=0)
    workspace, commit_sha = await clone.clone_repo(
        session_id=session_id,
        installation_id=_resolve_installation_id(session_row),
        repo_full_name=str(session_row.repo_full_name),
        branch=str(session_row.repo_branch),
    )
    session_row.commit_sha = commit_sha  # type: ignore[assignment]
    await db.commit()
    await _update_status(db, session_id, status="analyzing", progress=15)

    # Step 2 scan
    scan_result = scan.scan_workspace(workspace)
    await _update_status(db, session_id, status="analyzing", progress=35)

    # Step 3 manifest
    manifest_result = manifest.parse_manifests(workspace)
    await _update_status(db, session_id, status="analyzing", progress=55)

    # Step 4 outdated
    outdated_result = await outdated.detect_outdated(
        manifests=manifest_result["manifests"],  # type: ignore[arg-type]
        framework_signals=manifest_result["framework_signals"],  # type: ignore[arg-type]
    )
    await _update_status(db, session_id, status="analyzing", progress=70)

    # Step 5 sample
    snippets = sample.sample_workspace(workspace)
    await _update_status(db, session_id, status="recommending", progress=80)

    # Step 6 LLM summary
    summary_md, tokens_used = await llm_summary.summarize_codebase(
        scenario=str(session_row.scenario),
        goals_text=str(session_row.goals_text or ""),
        lang_distribution=scan_result["lang_distribution"],  # type: ignore[arg-type]
        framework_signals=manifest_result["framework_signals"],  # type: ignore[arg-type]
        outdated_packages=outdated_result["outdated_packages"],  # type: ignore[arg-type]
        snippets=snippets,
    )
    await _update_status(db, session_id, status="recommending", progress=85)

    # Step 7 권장안 생성 (M6) — 시나리오별 LLM 호출 또는 deterministic fallback
    recs = await recommendations_svc.generate_recommendations(
        scenario=str(session_row.scenario),
        goals_text=str(session_row.goals_text or ""),
        lang_distribution=scan_result["lang_distribution"],  # type: ignore[arg-type]
        framework_signals=manifest_result["framework_signals"],  # type: ignore[arg-type]
        outdated_packages=outdated_result["outdated_packages"],  # type: ignore[arg-type]
        manifests=manifest_result["manifests"],  # type: ignore[arg-type]
        llm_summary=summary_md,
    )
    await _upsert_recommendations(db, session_id=session_id, recs=recs)
    await _update_status(db, session_id, status="recommending", progress=95)

    # 결과 영속 — CodebaseAnalysis upsert (1:1)
    await _upsert_analysis(
        db,
        session_id=session_id,
        scan_result=scan_result,
        manifest_result=manifest_result,
        outdated_result=outdated_result,
        summary_md=summary_md,
        tokens_used=tokens_used,
    )

    # M6 에서 권장안 생성 단계 추가 예정. M5 는 ready 로 마무리.
    await _update_status(db, session_id, status="ready", progress=100)


def _resolve_installation_id(session_row: ModernizeSession) -> int:
    """ModernizeSession 의 installation_id (FK UUID) 를 GitHub installation_id (int) 로 변환.

    pipeline 함수는 GitHub 측 installation_id 가 필요. session_row 는 FK 만 갖고 있어
    별도 조회가 필요하지만, MVP-2-A 단계에서는 session_row 의 extra jsonb 에 저장하거나
    별도 query 로 조회. 여기서는 단순화: clone.clone_repo 가 GitHub 측 id 를 직접 받음 →
    추후 endpoint 가 POST /sessions 시 GitHub 측 id 를 함께 받아 extra 에 저장.
    """
    extra = session_row.extra
    if isinstance(extra, dict):
        gh_id = extra.get("github_installation_id")
        if isinstance(gh_id, int):
            return gh_id
    raise RuntimeError(
        "session.extra.github_installation_id 가 설정되지 않아 clone 할 수 없습니다."
    )


async def _load_session(db: AsyncSession, session_id: UUID) -> ModernizeSession | None:
    result = await db.execute(select(ModernizeSession).where(ModernizeSession.id == session_id))
    return result.scalar_one_or_none()


async def _update_status(db: AsyncSession, session_id: UUID, *, status: str, progress: int) -> None:
    result = await db.execute(select(ModernizeSession).where(ModernizeSession.id == session_id))
    row = result.scalar_one_or_none()
    if row is None:
        return
    row.status = status  # type: ignore[assignment]
    row.progress_pct = progress  # type: ignore[assignment]
    await db.commit()


async def _mark_failed(db: AsyncSession, session_id: UUID, *, error_message: str) -> None:
    async with async_session() as db_new:
        result = await db_new.execute(
            select(ModernizeSession).where(ModernizeSession.id == session_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.status = "failed"  # type: ignore[assignment]
        row.error = {  # type: ignore[assignment]
            "message": error_message,
            "occurred_at": datetime.now(UTC).isoformat(),
        }
        await db_new.commit()


async def _upsert_analysis(
    db: AsyncSession,
    *,
    session_id: UUID,
    scan_result: dict,  # type: ignore[type-arg]
    manifest_result: dict,  # type: ignore[type-arg]
    outdated_result: dict,  # type: ignore[type-arg]
    summary_md: str,
    tokens_used: int,
) -> None:
    result = await db.execute(
        select(CodebaseAnalysis).where(CodebaseAnalysis.session_id == session_id)
    )
    row = result.scalar_one_or_none()
    now = datetime.now(UTC)

    fields = {
        "loc_total": scan_result.get("loc_total"),
        "file_count": scan_result.get("file_count"),
        "lang_distribution": scan_result.get("lang_distribution") or {},
        "manifests": manifest_result.get("manifests") or [],
        "outdated_packages": outdated_result.get("outdated_packages") or [],
        "framework_signals": manifest_result.get("framework_signals") or {},
        "risk_flags": outdated_result.get("risk_flags") or [],
        "llm_summary_md": summary_md,
        "tokens_used": tokens_used,
        "analyzed_at": now,
    }

    if row is None:
        row = CodebaseAnalysis(session_id=session_id, **fields)
        db.add(row)
    else:
        for k, v in fields.items():
            setattr(row, k, v)
    await db.commit()


async def _upsert_recommendations(
    db: AsyncSession,
    *,
    session_id: UUID,
    recs: list[dict[str, object]],
) -> None:
    """기존 세션의 권장안 모두 삭제 후 새로 insert (재분석 시 깔끔).

    M7 finalize 후 linear_issue_id 가 채워져도, 재분석 시 그 정보는 손실됨 — MVP 단순화.
    M7+ 에서는 finalize 후 ModernizeSession.status='finalized' 이면 재분석 차단 또는
    권장안 보존 정책 도입 검토.
    """
    # 기존 권장안 삭제
    existing = await db.execute(
        select(ModernizeRecommendation).where(ModernizeRecommendation.session_id == session_id)
    )
    for row in existing.scalars().all():
        await db.delete(row)
    await db.flush()

    # 새 권장안 insert
    for idx, rec in enumerate(recs):
        row = ModernizeRecommendation(
            session_id=session_id,
            idx=idx,
            category=str(rec.get("category", "upgrade")),
            target_path=_cast_str_or_none(rec.get("target_path")),
            before=rec.get("before") if isinstance(rec.get("before"), dict) else None,
            after=rec.get("after") if isinstance(rec.get("after"), dict) else None,
            title=str(rec.get("title", ""))[:300],
            rationale_md=_cast_str_or_none(rec.get("rationale_md")),
            effort=str(rec.get("effort", "M"))[:2],
            risk=str(rec.get("risk", "med"))[:10],
            priority=_extract_priority(rec.get("priority")),
            prompt_md=_cast_str_or_none(rec.get("prompt_md")),
            selected=True,
        )
        db.add(row)
    await db.commit()


def _cast_str_or_none(v: object) -> str | None:
    if isinstance(v, str) and v:
        return v
    return None


def _extract_priority(v: object) -> int:
    if isinstance(v, int) and not isinstance(v, bool):
        return max(1, min(100, v))
    return 50
