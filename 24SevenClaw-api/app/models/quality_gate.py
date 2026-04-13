"""품질 검증 게이트 모델.

Step 07 품질 검증을 자동화하기 위한 모델:
- QualityGateRun: 검증 실행 단위 (세션당 N회 가능)
- QualityCheck: 개별 메트릭 검사 결과 (코드 품질, 보안, 성능 등)
- QualityGateEvent: 검증 이벤트 이력
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.sqlite import JSON

from app.database import Base


class QualityGateRun(Base):
    """품질 검증 실행 — 세션 내 한 번의 검증 사이클."""

    __tablename__ = "quality_gate_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(
        Uuid,
        ForeignKey("orchestrator_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_id = Column(
        Uuid,
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    run_number = Column(Integer, nullable=False, default=1)
    status = Column(String(20), nullable=False, default="pending")
    # 집계 결과
    overall_score = Column(Integer, nullable=True)  # 0~100
    threshold = Column(Integer, nullable=False, default=70)
    checks_total = Column(Integer, nullable=False, default=0)
    checks_passed = Column(Integer, nullable=False, default=0)
    verdict = Column(String(20), nullable=True)  # "approved" | "rejected"
    verdict_reason = Column(Text, nullable=True)
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    completed_at = Column(DateTime(timezone=True), nullable=True)


class QualityCheck(Base):
    """개별 품질 메트릭 검사 결과."""

    __tablename__ = "quality_checks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id = Column(
        Uuid,
        ForeignKey("quality_gate_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # code_quality, security, performance, test_coverage, documentation
    category = Column(String(30), nullable=False)
    score = Column(Integer, nullable=False)  # 0~100
    passed = Column(String(5), nullable=False, default="false")  # "true" | "false"
    agent_id = Column(String(100), nullable=True)  # QA 에이전트 식별자
    details = Column(Text, nullable=True)  # 상세 검사 결과
    findings = Column(JSON, nullable=True)  # 구조화된 발견 사항
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class QualityGateEvent(Base):
    """품질 검증 이벤트 이력."""

    __tablename__ = "quality_gate_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    run_id = Column(
        Uuid,
        ForeignKey("quality_gate_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False)
    actor_type = Column(String(20), nullable=False)  # user, agent, system
    actor_id = Column(Uuid, nullable=True)
    message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
