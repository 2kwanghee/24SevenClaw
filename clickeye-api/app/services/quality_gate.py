"""품질 검증 게이트 서비스.

Step 07 품질 검증을 자동화한다.
- 품질 메트릭 수집 (코드 품질, 보안, 성능, 테스트 커버리지, 문서화)
- 검증 통과/실패 기준 (threshold) 기반 평가
- 검증 결과에 따른 상태 머신 자동 전이
  - 통과 → Approved (orchestrator: validating → approved)
  - 실패 → 재작업 (orchestrator: validating → integrating)
- QA 에이전트 카탈로그 연동
- 검증 결과 리포트 생성
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.artifact import Artifact
from app.models.orchestrator import OrchestratorSession
from app.models.quality_gate import QualityCheck, QualityGateEvent, QualityGateRun
from app.schemas.quality_gate import (
    QualityCheckSubmit,
    QualityGateRunCreate,
)

# 허용 카테고리
VALID_CATEGORIES: set[str] = {
    "code_quality",
    "security",
    "performance",
    "test_coverage",
    "documentation",
}

# 검증 실행 상태 전이 맵
GATE_RUN_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["running"],
    "running": ["passed", "failed"],
    "passed": [],
    "failed": [],
}


class QualityGateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # === 검증 실행 생성 ===

    async def create_run(
        self,
        session_id: UUID,
        data: QualityGateRunCreate,
    ) -> QualityGateRun:
        """새 품질 검증 실행을 생성한다. validating 단계에서만 가능."""
        session = await self._get_session(session_id)

        if session.phase != "validating":
            raise AppError(
                "INVALID_PHASE",
                f"품질 검증은 'validating' 단계에서만 가능합니다. "
                f"현재: '{session.phase}'",
                422,
            )

        # artifact 존재 확인
        if data.artifact_id:
            artifact = await self.db.get(Artifact, data.artifact_id)
            if artifact is None:
                raise AppError("ARTIFACT_NOT_FOUND", "산출물을 찾을 수 없습니다.", 404)

        # 현재 세션의 실행 횟수 조회
        count_stmt = (
            select(func.count())
            .select_from(QualityGateRun)
            .where(QualityGateRun.session_id == session_id)
        )
        run_count = (await self.db.execute(count_stmt)).scalar_one()

        run = QualityGateRun(
            session_id=session_id,
            artifact_id=data.artifact_id,
            run_number=run_count + 1,
            status="pending",
            threshold=data.threshold,
        )
        self.db.add(run)
        await self.db.flush()

        # 이벤트 기록
        event = QualityGateEvent(
            run_id=run.id,
            event_type="run_created",
            actor_type="system",
            message=f"품질 검증 #{run.run_number} 생성 — 기준 점수: {data.threshold}",
            metadata_json={"threshold": data.threshold},
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(run)
        return run

    # === 개별 검사 결과 제출 ===

    async def submit_check(
        self,
        run_id: UUID,
        data: QualityCheckSubmit,
    ) -> QualityCheck:
        """QA 에이전트가 개별 메트릭 검사 결과를 제출한다."""
        run = await self._get_run(run_id)

        if run.status not in ("pending", "running"):
            raise AppError(
                "INVALID_STATUS",
                f"검사 제출은 'pending' 또는 'running' 상태에서만 가능합니다. "
                f"현재: '{run.status}'",
                422,
            )

        # 같은 카테고리 중복 제출 방지
        dup_stmt = (
            select(func.count())
            .select_from(QualityCheck)
            .where(
                QualityCheck.run_id == run_id,
                QualityCheck.category == data.category,
            )
        )
        dup_count = (await self.db.execute(dup_stmt)).scalar_one()
        if dup_count > 0:
            raise AppError(
                "DUPLICATE_CHECK",
                f"'{data.category}' 카테고리 검사는 이미 제출되었습니다.",
                409,
            )

        # pending → running 자동 전이
        if run.status == "pending":
            run.status = "running"

        passed = "true" if data.score >= run.threshold else "false"

        check = QualityCheck(
            run_id=run_id,
            category=data.category,
            score=data.score,
            passed=passed,
            agent_id=data.agent_id,
            details=data.details,
            findings=data.findings,
        )
        self.db.add(check)

        # 집계 업데이트
        run.checks_total += 1
        if passed == "true":
            run.checks_passed += 1

        # 이벤트 기록
        event = QualityGateEvent(
            run_id=run_id,
            event_type="check_submitted",
            actor_type="agent" if data.agent_id else "system",
            message=(
                f"{data.category} 검사 완료 — 점수: {data.score}/{run.threshold} "
                f"({'통과' if passed == 'true' else '미달'})"
            ),
            metadata_json={
                "category": data.category,
                "score": data.score,
                "passed": passed == "true",
                "agent_id": data.agent_id,
            },
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(check)
        return check

    # === 검증 평가 (최종 판정) ===

    async def evaluate(
        self,
        run_id: UUID,
        auto_transition: bool = True,
    ) -> QualityGateRun:
        """모든 검사 결과를 종합하여 통과/실패를 판정한다."""
        run = await self._get_run(run_id)

        if run.status != "running":
            raise AppError(
                "INVALID_STATUS",
                f"평가는 'running' 상태에서만 가능합니다. 현재: '{run.status}'",
                422,
            )

        if run.checks_total == 0:
            raise AppError(
                "NO_CHECKS",
                "제출된 검사 결과가 없습니다.",
                422,
            )

        # 전체 점수 계산 (가중 평균)
        checks = await self._get_checks(run_id)
        total_score = sum(c.score for c in checks)
        run.overall_score = total_score // len(checks)

        # 판정
        all_passed = all(c.passed == "true" for c in checks)
        if all_passed and run.overall_score >= run.threshold:
            run.status = "passed"
            run.verdict = "approved"
            run.verdict_reason = (
                f"모든 검사 통과 — 종합 점수: {run.overall_score}/{run.threshold}"
            )
        else:
            run.status = "failed"
            run.verdict = "rejected"
            failed_categories = [c.category for c in checks if c.passed != "true"]
            run.verdict_reason = (
                f"검사 미달 항목: {', '.join(failed_categories)} — "
                f"종합 점수: {run.overall_score}/{run.threshold}"
            )

        run.completed_at = datetime.now(UTC)

        # 이벤트 기록
        event = QualityGateEvent(
            run_id=run_id,
            event_type="evaluated",
            actor_type="system",
            message=run.verdict_reason,
            metadata_json={
                "verdict": run.verdict,
                "overall_score": run.overall_score,
                "checks_passed": run.checks_passed,
                "checks_total": run.checks_total,
            },
        )
        self.db.add(event)

        # 상태 자동 전이
        if auto_transition:
            await self._auto_transition(run)

        await self.db.commit()
        await self.db.refresh(run)
        return run

    # === 리포트 조회 ===

    async def get_report(
        self, run_id: UUID
    ) -> tuple[QualityGateRun, list[QualityCheck]]:
        """검증 결과 리포트를 조회한다."""
        run = await self._get_run(run_id)
        checks = await self._get_checks(run_id)
        return run, checks

    # === 실행 조회 ===

    async def get_run(self, run_id: UUID) -> QualityGateRun:
        return await self._get_run(run_id)

    async def list_runs(
        self,
        session_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[QualityGateRun], int]:
        await self._get_session(session_id)

        count_stmt = (
            select(func.count())
            .select_from(QualityGateRun)
            .where(QualityGateRun.session_id == session_id)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(QualityGateRun)
            .where(QualityGateRun.session_id == session_id)
            .order_by(QualityGateRun.run_number.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        runs = list(result.scalars().all())
        return runs, total

    # === 이벤트 이력 ===

    async def get_events(self, run_id: UUID) -> list[QualityGateEvent]:
        await self._get_run(run_id)
        stmt = (
            select(QualityGateEvent)
            .where(QualityGateEvent.run_id == run_id)
            .order_by(QualityGateEvent.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # === 내부 헬퍼 ===

    async def _get_session(self, session_id: UUID) -> OrchestratorSession:
        session = await self.db.get(OrchestratorSession, session_id)
        if session is None:
            raise AppError("SESSION_NOT_FOUND", "오케스트레이션 세션을 찾을 수 없습니다.", 404)
        return session

    async def _get_run(self, run_id: UUID) -> QualityGateRun:
        run = await self.db.get(QualityGateRun, run_id)
        if run is None:
            raise AppError("GATE_RUN_NOT_FOUND", "품질 검증 실행을 찾을 수 없습니다.", 404)
        return run

    async def _get_checks(self, run_id: UUID) -> list[QualityCheck]:
        stmt = (
            select(QualityCheck)
            .where(QualityCheck.run_id == run_id)
            .order_by(QualityCheck.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _auto_transition(self, run: QualityGateRun) -> None:
        """검증 결과에 따라 오케스트레이터 세션 상태를 자동 전이한다."""
        session = await self._get_session(run.session_id)

        if session.phase != "validating":
            return  # validating 단계가 아니면 전이 안 함

        if run.verdict == "approved":
            # validating → approved
            session.phase = "approved"
            session.updated_at = datetime.now(UTC)

            event = QualityGateEvent(
                run_id=run.id,
                event_type="auto_transition",
                actor_type="system",
                message="품질 검증 통과 → 세션 'approved' 전이",
                metadata_json={"old_phase": "validating", "new_phase": "approved"},
            )
            self.db.add(event)

            # artifact도 validated로 전이 (in_development → validated)
            if run.artifact_id:
                artifact = await self.db.get(Artifact, run.artifact_id)
                if artifact and artifact.status == "in_development":
                    artifact.status = "validated"
                    artifact.updated_at = datetime.now(UTC)

        elif run.verdict == "rejected":
            # validating → integrating (재작업)
            session.phase = "integrating"
            session.updated_at = datetime.now(UTC)

            event = QualityGateEvent(
                run_id=run.id,
                event_type="auto_transition",
                actor_type="system",
                message="품질 검증 실패 → 세션 'integrating' 전이 (재작업)",
                metadata_json={"old_phase": "validating", "new_phase": "integrating"},
            )
            self.db.add(event)
