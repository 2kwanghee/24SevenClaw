"""Modernize 6단계 Phase 모델 병행 도입 (asis/requirements/tobe/plan/preflight/execute).

비침습성 원칙: 기존 `status` 파이프라인/컬럼/인덱스는 어느 것도 건드리지 않는다.
변경은 (1) `modernize_sessions.current_phase` nullable=False + server_default 컬럼 추가,
(2) 신규 테이블 `modernize_phase_artifacts` 생성 뿐이며, downgrade 로 완전히 복원된다.

Revision ID: 042
Revises: 96e8e503b069
Create Date: 2026-07-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "042"
down_revision: str | None = "96e8e503b069"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ----------------------------------------------------------------------
    # 1) modernize_sessions.current_phase — 위저드 단계 축 (status 와 병행)
    # ----------------------------------------------------------------------
    op.add_column(
        "modernize_sessions",
        sa.Column(
            "current_phase",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'asis'"),
        ),
    )

    # ----------------------------------------------------------------------
    # 2) modernize_phase_artifacts — 단계별 산출물 (session_id 1:N)
    # ----------------------------------------------------------------------
    op.create_table(
        "modernize_phase_artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("phase", sa.String(length=20), nullable=False),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["modernize_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_modernize_phase_artifacts_session_id",
        "modernize_phase_artifacts",
        ["session_id"],
    )
    op.create_index(
        "ix_modernize_phase_artifacts_session_phase",
        "modernize_phase_artifacts",
        ["session_id", "phase"],
    )


def downgrade() -> None:
    # 신규 테이블 + 컬럼만 역순 삭제 — 042 이전 스키마와 완전히 동일하게 복원(회귀 안전).
    op.drop_index(
        "ix_modernize_phase_artifacts_session_phase",
        table_name="modernize_phase_artifacts",
    )
    op.drop_index(
        "ix_modernize_phase_artifacts_session_id",
        table_name="modernize_phase_artifacts",
    )
    op.drop_table("modernize_phase_artifacts")

    op.drop_column("modernize_sessions", "current_phase")
