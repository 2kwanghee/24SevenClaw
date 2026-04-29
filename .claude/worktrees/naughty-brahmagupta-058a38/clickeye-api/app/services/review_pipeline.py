"""교차 리뷰 파이프라인 서비스.

메인+서브 AI 구조를 실행 가능한 교차 리뷰 파이프라인으로 구현한다.
- 메인 AI: 초안 작성 / 방향 설정
- 서브 AI: 검토 / 보완 / 반론 / 대안

10단계 오케스트레이션 중 04(초안)→05(교차리뷰)→06(수정통합) 자동화.
"""

import difflib
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.orchestrator import OrchestratorSession, SubTask
from app.models.review_pipeline import ReviewEvent, ReviewRound
from app.schemas.review_pipeline import (
    MergeRequest,
    ReviewPrompt,
    ReviewRoundCreate,
    ReviewSubmit,
)
from app.services.artifact_service import ArtifactService
from app.services.claude_service import ClaudeService

logger = logging.getLogger(__name__)

# 리뷰 라운드 상태 전이 맵
REVIEW_TRANSITIONS: dict[str, list[str]] = {
    "draft_submitted": ["review_in_progress"],
    "review_in_progress": ["review_completed"],
    "review_completed": ["merged", "rejected"],
    "merged": [],
    "rejected": [],
}

# 리뷰 타입별 프롬프트 지침
REVIEW_INSTRUCTIONS: dict[str, str] = {
    "cross_review": (
        "초안을 면밀히 검토하고 다음을 포함하여 피드백을 제공하라:\n"
        "1. 정확성 검증 — 기술적 오류나 논리적 결함\n"
        "2. 완성도 평가 — 누락된 요구사항이나 엣지 케이스\n"
        "3. 개선 제안 — 구체적인 코드/설계 개선 방안\n"
        "4. 품질 점수 (0~100) — 전반적 품질 평가"
    ),
    "counter_argument": (
        "초안의 접근 방식에 대해 비판적으로 분석하라:\n"
        "1. 잠재적 문제점 — 확장성, 유지보수성, 성능 이슈\n"
        "2. 대안적 관점 — 다른 아키텍처/설계 패턴 제시\n"
        "3. 트레이드오프 분석 — 현재 방식 vs 대안의 장단점\n"
        "4. 최종 권고 — 현재 방식 유지 or 대안 채택 권고"
    ),
    "alternative": (
        "초안과 동일한 요구사항을 완전히 다른 방식으로 구현하라:\n"
        "1. 대안 구현 — 다른 기술/패턴/아키텍처 사용\n"
        "2. 차별점 설명 — 원본 대비 어떤 점이 다른지\n"
        "3. 장단점 비교 — 원본 vs 대안의 객관적 비교\n"
        "4. 추천 사유 — 대안이 더 나은 이유 (해당 시)"
    ),
}


class ReviewPipelineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # === 초안 제출 (04단계: drafting) ===

    async def submit_draft(
        self,
        session_id: UUID,
        data: ReviewRoundCreate,
    ) -> ReviewRound:
        """메인 AI 초안을 제출하고 리뷰 라운드를 생성한다."""
        session = await self._get_session(session_id)

        # drafting 또는 reviewing 단계에서만 초안 제출 가능
        if session.phase not in ("drafting", "reviewing"):
            raise AppError(
                "INVALID_PHASE",
                f"초안 제출은 'drafting' 또는 'reviewing' 단계에서만 가능합니다. "
                f"현재: '{session.phase}'",
                422,
            )

        # 현재 세션의 라운드 수 조회
        count_stmt = (
            select(func.count())
            .select_from(ReviewRound)
            .where(ReviewRound.session_id == session_id)
        )
        round_count = (await self.db.execute(count_stmt)).scalar_one()

        review_round = ReviewRound(
            session_id=session_id,
            subtask_id=data.subtask_id,
            round_number=round_count + 1,
            status="draft_submitted",
            main_ai_role=data.main_ai_role,
            draft_content=data.draft_content,
        )
        self.db.add(review_round)
        await self.db.flush()

        # 이벤트 기록
        event = ReviewEvent(
            round_id=review_round.id,
            event_type="draft_submitted",
            actor_type="agent",
            message=f"메인 AI({data.main_ai_role}) 초안 제출 — 라운드 {review_round.round_number}",
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(review_round)
        return review_round

    # === 교차 리뷰 제출 (05단계: reviewing) ===

    async def submit_review(
        self,
        round_id: UUID,
        data: ReviewSubmit,
    ) -> ReviewRound:
        """서브 AI 교차 리뷰를 제출한다."""
        review_round = await self._get_round(round_id)

        if review_round.status not in ("draft_submitted", "review_in_progress"):
            raise AppError(
                "INVALID_STATUS",
                f"리뷰 제출은 'draft_submitted' 또는 'review_in_progress' 상태에서만 "
                f"가능합니다. 현재: '{review_round.status}'",
                422,
            )

        review_round.sub_ai_role = data.sub_ai_role
        review_round.review_type = data.review_type
        review_round.review_content = data.review_content
        review_round.review_score = data.review_score
        review_round.status = "review_completed"
        review_round.updated_at = datetime.now(UTC)

        # diff 자동 생성
        review_round.diff_summary = self._generate_diff(
            review_round.draft_content, data.review_content
        )

        # 이벤트 기록
        event = ReviewEvent(
            round_id=round_id,
            event_type="review_submitted",
            actor_type="agent",
            message=f"서브 AI({data.sub_ai_role}) {data.review_type} 리뷰 완료",
            metadata_json={"review_score": data.review_score, "review_type": data.review_type},
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(review_round)
        return review_round

    # === diff 조회 ===

    async def get_diff(self, round_id: UUID) -> ReviewRound:
        """리뷰 라운드의 diff를 조회한다."""
        review_round = await self._get_round(round_id)

        if not review_round.review_content:
            raise AppError(
                "NO_REVIEW",
                "아직 리뷰가 제출되지 않았습니다.",
                422,
            )

        # diff가 아직 없으면 생성
        if not review_round.diff_summary:
            review_round.diff_summary = self._generate_diff(
                review_round.draft_content, review_round.review_content
            )
            await self.db.commit()
            await self.db.refresh(review_round)

        return review_round

    # === 병합 (06단계: integrating) ===

    async def merge(
        self,
        round_id: UUID,
        data: MergeRequest,
    ) -> ReviewRound:
        """리뷰 결과를 병합한다."""
        review_round = await self._get_round(round_id)

        if review_round.status != "review_completed":
            raise AppError(
                "INVALID_STATUS",
                f"병합은 'review_completed' 상태에서만 가능합니다. "
                f"현재: '{review_round.status}'",
                422,
            )

        review_round.merge_strategy = data.merge_strategy

        if data.merge_strategy == "accept_draft":
            review_round.merged_content = review_round.draft_content
        elif data.merge_strategy == "accept_review":
            review_round.merged_content = review_round.review_content
        elif data.merge_strategy == "manual_merge":
            if not data.merged_content:
                raise AppError(
                    "MERGE_CONTENT_REQUIRED",
                    "manual_merge 전략은 merged_content가 필수입니다.",
                    422,
                )
            review_round.merged_content = data.merged_content

        review_round.status = "merged"
        review_round.updated_at = datetime.now(UTC)

        # 이벤트 기록
        event = ReviewEvent(
            round_id=round_id,
            event_type="merged",
            actor_type="system",
            message=f"병합 완료 — 전략: {data.merge_strategy}",
            metadata_json={"merge_strategy": data.merge_strategy},
        )
        self.db.add(event)

        # 병합 후 SubTask → completed, Artifact → reviewed 자동 전이
        if review_round.subtask_id:
            subtask = await self.db.get(SubTask, review_round.subtask_id)
            if subtask is not None:
                subtask.status = "completed"
                subtask.updated_at = datetime.now(UTC)

                if subtask.artifact_id is not None:
                    artifact_svc = ArtifactService(self.db)
                    await artifact_svc.bulk_transition(
                        artifact_ids=[subtask.artifact_id],
                        target_status="reviewed",
                        actor_type="system",
                        message=f"리뷰 라운드 병합({data.merge_strategy})에 의한 자동 전이",
                    )

        await self.db.commit()
        await self.db.refresh(review_round)
        return review_round

    # === 거절 (reviewing → drafting 사이클) ===

    async def reject(
        self,
        round_id: UUID,
        reason: str,
    ) -> ReviewRound:
        """리뷰 결과를 거절하고 재작성을 요청한다."""
        review_round = await self._get_round(round_id)

        if review_round.status != "review_completed":
            raise AppError(
                "INVALID_STATUS",
                f"거절은 'review_completed' 상태에서만 가능합니다. "
                f"현재: '{review_round.status}'",
                422,
            )

        review_round.status = "rejected"
        review_round.updated_at = datetime.now(UTC)

        # 이벤트 기록
        event = ReviewEvent(
            round_id=round_id,
            event_type="rejected",
            actor_type="system",
            message=f"리뷰 거절 — 사유: {reason}",
        )
        self.db.add(event)

        await self.db.commit()
        await self.db.refresh(review_round)
        return review_round

    # === 리뷰 라운드 조회 ===

    async def list_rounds(
        self,
        session_id: UUID,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[ReviewRound], int]:
        """세션의 리뷰 라운드 목록을 조회한다."""
        await self._get_session(session_id)

        count_stmt = (
            select(func.count())
            .select_from(ReviewRound)
            .where(ReviewRound.session_id == session_id)
        )
        total = (await self.db.execute(count_stmt)).scalar_one()

        stmt = (
            select(ReviewRound)
            .where(ReviewRound.session_id == session_id)
            .order_by(ReviewRound.round_number.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rounds = list(result.scalars().all())
        return rounds, total

    async def get_round(self, round_id: UUID) -> ReviewRound:
        """리뷰 라운드 상세 조회."""
        return await self._get_round(round_id)

    # === 이벤트 이력 ===

    async def get_events(self, round_id: UUID) -> list[ReviewEvent]:
        """리뷰 라운드의 이벤트 이력을 조회한다."""
        await self._get_round(round_id)
        stmt = (
            select(ReviewEvent)
            .where(ReviewEvent.round_id == round_id)
            .order_by(ReviewEvent.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # === 프롬프트 생성 ===

    async def build_review_prompt(
        self,
        round_id: UUID,
        review_type: str = "cross_review",
    ) -> ReviewPrompt:
        """교차 리뷰용 표준 프롬프트를 생성한다."""
        review_round = await self._get_round(round_id)
        session = await self._get_session(review_round.session_id)

        subtask_title: str | None = None
        if review_round.subtask_id:
            subtask = await self.db.get(SubTask, review_round.subtask_id)
            if subtask:
                subtask_title = subtask.title

        instructions = REVIEW_INSTRUCTIONS.get(review_type, REVIEW_INSTRUCTIONS["cross_review"])

        return ReviewPrompt(
            session_title=session.title,
            subtask_title=subtask_title,
            main_ai_role=review_round.main_ai_role,
            draft_content=review_round.draft_content,
            review_type=review_type,  # type: ignore[arg-type]
            instructions=instructions,
        )

    # === Claude 자동 리뷰 생성 ===

    async def generate_review(
        self,
        round_id: UUID,
        review_type: str = "cross_review",
        sub_ai_role: str = "reviewer",
    ) -> ReviewRound:
        """교차 리뷰 라운드를 자동 완료 처리한다. 실제 리뷰는 로컬 파이프라인에서 수행된다."""
        review_prompt = await self.build_review_prompt(round_id, review_type)
        review_content = (
            f"[웹 파이프라인 자동 승인] {review_prompt.session_title} — "
            f"{review_prompt.subtask_title or ''}\n\n"
            "실제 코드 리뷰 및 구현은 로컬 Claude Code 파이프라인에서 처리됩니다."
        )
        return await self.submit_review(
            round_id=round_id,
            data=ReviewSubmit(
                sub_ai_role=sub_ai_role,
                review_type=review_type,  # type: ignore[arg-type]
                review_content=review_content,
                review_score=None,
            ),
        )

    # === 내부 헬퍼 ===

    async def _get_session(self, session_id: UUID) -> OrchestratorSession:
        session = await self.db.get(OrchestratorSession, session_id)
        if session is None:
            raise AppError("SESSION_NOT_FOUND", "오케스트레이션 세션을 찾을 수 없습니다.", 404)
        return session

    async def _get_round(self, round_id: UUID) -> ReviewRound:
        review_round = await self.db.get(ReviewRound, round_id)
        if review_round is None:
            raise AppError("REVIEW_ROUND_NOT_FOUND", "리뷰 라운드를 찾을 수 없습니다.", 404)
        return review_round

    @staticmethod
    def _generate_diff(draft: str, review: str) -> str:
        """초안과 리뷰 내용 간 unified diff를 생성한다."""
        draft_lines = draft.splitlines(keepends=True)
        review_lines = review.splitlines(keepends=True)

        diff = difflib.unified_diff(
            draft_lines,
            review_lines,
            fromfile="draft",
            tofile="review",
            lineterm="",
        )
        diff_text = "\n".join(diff)
        return diff_text if diff_text else "(변경 없음)"
