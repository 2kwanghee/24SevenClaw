from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

ReviewRoundStatusType = Literal[
    "draft_submitted",
    "review_in_progress",
    "review_completed",
    "merged",
    "rejected",
]

ReviewTypeType = Literal[
    "cross_review",
    "counter_argument",
    "alternative",
]

MergeStrategyType = Literal[
    "accept_draft",
    "accept_review",
    "manual_merge",
]


# === 리뷰 라운드 ===


class ReviewRoundCreate(BaseModel):
    """메인 AI 초안 제출 (drafting → reviewing 트리거)."""

    subtask_id: UUID | None = None
    main_ai_role: str = Field(..., min_length=1, max_length=50)
    draft_content: str = Field(..., min_length=1)


class ReviewSubmit(BaseModel):
    """서브 AI 교차 리뷰 제출."""

    sub_ai_role: str = Field(..., min_length=1, max_length=50)
    review_type: ReviewTypeType = "cross_review"
    review_content: str = Field(..., min_length=1)
    review_score: int | None = Field(None, ge=0, le=100)


class MergeRequest(BaseModel):
    """리뷰 결과 병합 요청."""

    merge_strategy: MergeStrategyType
    merged_content: str | None = Field(None)
    message: str | None = Field(None, max_length=500)


class RejectRequest(BaseModel):
    """리뷰 거절 (drafting으로 되돌림)."""

    reason: str = Field(..., min_length=1, max_length=500)


class ReviewRoundResponse(BaseModel):
    id: UUID
    session_id: UUID
    subtask_id: UUID | None
    round_number: int
    status: str
    main_ai_role: str
    draft_content: str
    sub_ai_role: str | None
    review_type: str | None
    review_content: str | None
    review_score: int | None
    diff_summary: str | None
    merged_content: str | None
    merge_strategy: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewRoundListResponse(BaseModel):
    items: list[ReviewRoundResponse]
    total: int


class ReviewEventResponse(BaseModel):
    id: UUID
    round_id: UUID
    event_type: str
    actor_type: str
    actor_id: UUID | None
    message: str | None
    metadata_json: dict | None  # type: ignore[type-arg]
    created_at: datetime

    model_config = {"from_attributes": True}


class DiffResult(BaseModel):
    """diff 생성 결과."""

    round_id: UUID
    draft_content: str
    review_content: str
    diff_summary: str
    review_type: str | None


# === 프롬프트 체계 ===


class ReviewPrompt(BaseModel):
    """교차 리뷰용 프롬프트."""

    session_title: str
    subtask_title: str | None
    main_ai_role: str
    draft_content: str
    review_type: ReviewTypeType
    instructions: str


# === AI 초안 자동 생성 ===


class LinearSyncHintSubtask(BaseModel):
    title: str
    role: str
    draft_summary: str


class LinearSyncHint(BaseModel):
    """로컬 Agent(Claude Code)가 Linear에 이슈를 생성할 때 참고하는 힌트."""

    action: str = "create_issues"
    session_title: str
    session_description: str | None = None
    subtasks: list[LinearSyncHintSubtask]
    suggested_labels: list[str] = ["ai-team"]
    instructions: str = (
        "이 힌트를 참고해 Linear에 이슈를 생성하세요. "
        "각 subtask를 하나의 이슈로 생성하고 session_title을 프로젝트/에픽으로 연결하세요."
    )


class GenerateDraftsResponse(BaseModel):
    """AI 초안 자동 생성 결과."""

    rounds: list[ReviewRoundResponse]
    linear_sync_hint: LinearSyncHint


class PushToLinearResponse(BaseModel):
    """서버 대행 Linear 이슈 생성 결과."""

    created_identifiers: list[str]
    created_urls: list[str]
    count: int
    initial_state_applied: bool = False


class ApproveSubtaskResponse(BaseModel):
    """subtask 큐 등록(Wait → Queued) 결과."""

    subtask_id: UUID
    linear_identifier: str
    transitioned_to: str
