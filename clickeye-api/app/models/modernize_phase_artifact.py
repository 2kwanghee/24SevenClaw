"""Modernize 6단계 워크플로(asis/requirements/tobe/plan/preflight/execute)의 단계별 산출물.

`ModernizeSession.current_phase` 축과 병행 도입된다. 각 단계에서 사용자가 검수/승인하는
문서(마크다운) 또는 구조화 데이터(JSON)를 세션당 다건 영속한다. 예: requirements 단계의
As-Is/To-Be 스택 비교, plan 단계의 작업 계획서 등.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ModernizePhaseArtifact(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "modernize_phase_artifacts"

    session_id = Column(
        Uuid,
        ForeignKey("modernize_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 'asis' | 'requirements' | 'tobe' | 'plan' | 'preflight' | 'execute'
    phase = Column(String(20), nullable=False)
    # 산출물 구분 (자유 문자열) — 예: 'requirements_stack', 'plan_summary'
    artifact_type = Column(String(50), nullable=False)
    content_md = Column(Text, nullable=True)
    content_json = Column(JSON, nullable=True)
    # 사용자 검수 승인 시각 (미승인 시 NULL)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index(
            "ix_modernize_phase_artifacts_session_phase",
            "session_id",
            "phase",
        ),
    )
