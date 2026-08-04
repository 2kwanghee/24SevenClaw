"""파이프라인 실행 이력 원장 모델 (CE-363).

무인 파이프라인이 티켓 1건을 처리하는 동안 남기는 **단계별 이벤트**를 서버에 모은다.
지금까지 이 이력은 호스트 로컬 파일(`logs/metrics/pipeline_runs.jsonl`)에만 있어서
브라우저에서 볼 수 없었고, 워크스페이스별 러너가 늘어나면 흩어졌다.

설계 원칙:
- **로컬 jsonl 을 대체하지 않는다.** 파이프라인은 jsonl 기록과 함께 이 원장으로도 보낸다
  (서버가 죽어도 관측이 끊기지 않는다 — 비블로킹).
- 이벤트 이름은 `pipeline_metrics.py` 가 쓰는 값을 **그대로 승계**한다(refine_done ·
  impl_done · qa_done · gate_done · run_done · model_mismatch …). 서버에서 재해석하지 않고
  `data` 를 원형(JSONB)으로 보존해, 새 이벤트가 추가돼도 스키마 변경이 필요 없다.
- 멱등: `(run_id, event)` 유일. 재전송·재시도는 같은 행을 갱신한다(중복 적재 금지).
- 소비 토큰은 이 테이블이 **가지지 않는다.** `llm_usage_ledger` 가 `task_id`(= 이슈 키)·
  `project_id` 축으로 이미 보유하므로 조회 시점에 조인한다(단일 진실 유지).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class PipelineRunEvent(Base):
    """파이프라인 실행 1건(run)의 단계 이벤트 1행."""

    __tablename__ = "pipeline_run_events"
    __table_args__ = (
        # 멱등 키 — 같은 run 의 같은 이벤트는 하나뿐이다(재전송은 갱신).
        UniqueConstraint("run_id", "event", name="uq_pipeline_run_event"),
        # 화면의 두 진입점: 티켓별 스레드 / 프로젝트별 집계.
        Index("ix_pipeline_run_events_issue_key", "issue_key"),
        Index("ix_pipeline_run_events_project_id", "project_id"),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    # 파이프라인이 이터레이션마다 만드는 run 식별자(METRIC_RUN_ID). UUID 가 아닐 수 있어 문자열.
    run_id = Column(String(128), nullable=False)
    # Linear 이슈 키(CE-366 등). 티켓별 스레드 조회의 축.
    issue_key = Column(String(64), nullable=False)
    # 딜리버리 프로젝트. self-repo 실행은 프로젝트가 없으므로 nullable.
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    # 워크스페이스(고객 clone) 키. self-repo 는 NULL.
    workspace_key = Column(String(64), nullable=True)
    # pipeline_metrics.py 의 이벤트 이름을 그대로 쓴다(서버가 새 이름을 막지 않는다).
    event = Column(String(64), nullable=False)
    # 이벤트 페이로드 원형 보존(duration_s · outcome · verdict · intended/actual 모델 등).
    data = Column(JSONB, nullable=False, default=dict, server_default="{}")
    # 파이프라인이 이벤트를 만든 시각(로컬). 없으면 수신 시각으로 채운다.
    occurred_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
