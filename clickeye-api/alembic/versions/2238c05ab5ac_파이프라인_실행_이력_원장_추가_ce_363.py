"""파이프라인 실행 이력 원장 추가 (CE-363)

Revision ID: 2238c05ab5ac
Revises: 058
Create Date: 2026-08-04 20:41:38.090356

⚠️ 이 파일은 autogenerate 출력에서 **무관한 변경을 걷어낸** 것이다. 자동 생성본은
`roi_standards`·`pm_recommendation_logs` **테이블 삭제**와 `uq_org_membership_active` ·
`uq_llm_usage_ledger_session_model` **유니크 인덱스 삭제**, `skills`/`agents`/`hooks` 의
JSONB→JSON 타입 변경까지 포함하고 있었다. 원인은 그 모델들이 `app/models/__init__.py` 에
등록돼 있지 않아 autogenerate 가 "DB 에만 있는 것 = 지워야 할 것" 으로 판단한 것이다.
그대로 적용하면 데이터가 사라진다. 이 리비전은 **신규 테이블 생성만** 수행한다.
(등록 누락 자체는 별도 티켓 — 다음 autogenerate 도 같은 위험을 만든다.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = '2238c05ab5ac'
down_revision: Union[str, None] = '058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pipeline_run_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('run_id', sa.String(length=128), nullable=False),
        sa.Column('issue_key', sa.String(length=64), nullable=False),
        sa.Column('project_id', sa.Uuid(), nullable=True),
        sa.Column('workspace_key', sa.String(length=64), nullable=True),
        sa.Column('event', sa.String(length=64), nullable=False),
        sa.Column(
            'data',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='{}',
            nullable=False,
        ),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'event', name='uq_pipeline_run_event'),
    )
    op.create_index(
        'ix_pipeline_run_events_issue_key', 'pipeline_run_events', ['issue_key'], unique=False
    )
    op.create_index(
        'ix_pipeline_run_events_project_id', 'pipeline_run_events', ['project_id'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_pipeline_run_events_project_id', table_name='pipeline_run_events')
    op.drop_index('ix_pipeline_run_events_issue_key', table_name='pipeline_run_events')
    op.drop_table('pipeline_run_events')
