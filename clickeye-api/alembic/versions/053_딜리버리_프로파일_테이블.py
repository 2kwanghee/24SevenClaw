"""딜리버리 프로파일 테이블 추가 (다프로젝트화 P0 — 제어면 YAML 런타임 미러)

프로젝트별 거버넌스 정책(governance.policy.Policy.from_dict() 입력 형태)과 딜리버리
티어를 보관하는 delivery_profiles 테이블을 생성한다. 프로젝트당 1행(project_id unique).

⚠️ 정본(SSOT)이 아니라 **서비스 #2 가 생성한 제어면 YAML 의 런타임 미러**다
(docs/multiproject-delivery.md §3 — D-3 철회·D-14). 따라서 출처 인증 컬럼
(schema_version / source_signature / source_yaml / provenance)을 함께 둔다 —
기계 저작물의 신뢰 근거는 소유권이 아니라 서명·버전·출처 기록이다. P0 은 보관까지만,
서명 검증·거부 콜백은 P2 에서 배선한다.

기존 테이블은 건드리지 않는다(순수 additive). 프로파일이 없는 프로젝트는 기본 정책으로
폴백하므로 이 마이그레이션만으로는 어떤 판정도 바뀌지 않는다.

Revision ID: 053
Revises: 052
Create Date: 2026-07-27 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "053"
down_revision: str | None = "052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "delivery_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        # lite | standard | enterprise
        sa.Column("tier", sa.String(length=20), nullable=False, server_default=sa.text("'lite'")),
        # Policy.from_dict() 입력 JSON(YAML 파싱 결과). 빈 객체면 기본 정책 승계(static).
        sa.Column("policy", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        # ── 출처 인증(D-14) — 정본 YAML 의 수신 증거. 미수신(수동) 프로파일은 NULL. ──
        sa.Column("schema_version", sa.String(length=20), nullable=True),
        # 서비스 #2 서비스 키 서명. P2 이후 무인 경로는 NULL 프로파일을 신뢰하지 않는다.
        sa.Column("source_signature", sa.Text(), nullable=True),
        # 수신 YAML 원문 — 서명·해시 재검증 대상.
        sa.Column("source_yaml", sa.Text(), nullable=True),
        # 서비스 #2 의 선택 근거(템플릿 ID·선택 사유) — 기계 저작물의 출처 기록.
        sa.Column("provenance", sa.JSON(), nullable=True),
        # 내부 에이전트 쓰기 금지 표시. P0 은 플래그만 보관하고 집행하지 않는다.
        sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
    )
    # 프로젝트당 1개 — 조회 인덱스 겸 유일성 강제.
    op.create_index(
        "ix_delivery_profiles_project_id", "delivery_profiles", ["project_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_delivery_profiles_project_id", table_name="delivery_profiles")
    op.drop_table("delivery_profiles")
