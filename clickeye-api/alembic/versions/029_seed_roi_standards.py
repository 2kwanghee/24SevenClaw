"""roi_standards 기본 데이터 시드

직군별 일급, 솔루션 타입별 baseline 공수, 복잡도 계수 기본값 삽입.
시드 누락 시 ROI 계산이 0원으로 표시되므로 028과 함께 반드시 적용.

Revision ID: 029
Revises: 028
Create Date: 2026-04-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # role_rate — JSON 없음, 콜론 문제 없음
    op.execute("""
        INSERT INTO roi_standards (id, category, key, label, value_numeric, unit, display_order, is_active, created_at, updated_at)
        VALUES
          (gen_random_uuid(), 'role_rate', 'pm',       '프로젝트 매니저',    900000,  'KRW/day', 0, true, now(), now()),
          (gen_random_uuid(), 'role_rate', 'be',       '백엔드 개발자',      1000000, 'KRW/day', 1, true, now(), now()),
          (gen_random_uuid(), 'role_rate', 'fe',       '프론트엔드 개발자',  900000,  'KRW/day', 2, true, now(), now()),
          (gen_random_uuid(), 'role_rate', 'qa',       'QA 엔지니어',       600000,  'KRW/day', 3, true, now(), now()),
          (gen_random_uuid(), 'role_rate', 'designer', 'UI/UX 디자이너',    700000,  'KRW/day', 4, true, now(), now())
    """)

    # solution_effort — jsonb_build_object()으로 콜론 바인드 파라미터 문제 우회
    op.execute("""
        INSERT INTO roi_standards (id, category, key, label, value_json, unit, display_order, is_active, created_at, updated_at)
        VALUES
          (gen_random_uuid(), 'solution_effort', 'saas',          'SaaS',
           jsonb_build_object('pm',10,'be',20,'fe',15,'qa',8,'designer',5),
           'days', 0, true, now(), now()),
          (gen_random_uuid(), 'solution_effort', 'rest-api',      'REST API',
           jsonb_build_object('pm',5,'be',15,'fe',0,'qa',5,'designer',0),
           'days', 1, true, now(), now()),
          (gen_random_uuid(), 'solution_effort', 'fullstack',     '풀스택',
           jsonb_build_object('pm',12,'be',25,'fe',20,'qa',10,'designer',6),
           'days', 2, true, now(), now()),
          (gen_random_uuid(), 'solution_effort', 'internal-tool', '내부 도구',
           jsonb_build_object('pm',5,'be',10,'fe',8,'qa',4,'designer',2),
           'days', 3, true, now(), now()),
          (gen_random_uuid(), 'solution_effort', 'mvp',           'MVP',
           jsonb_build_object('pm',6,'be',12,'fe',10,'qa',3,'designer',3),
           'days', 4, true, now(), now()),
          (gen_random_uuid(), 'solution_effort', 'custom',        '커스텀',
           jsonb_build_object('pm',10,'be',18,'fe',12,'qa',6,'designer',4),
           'days', 5, true, now(), now())
    """)

    # complexity_multiplier — JSON 없음, 콜론 문제 없음
    op.execute("""
        INSERT INTO roi_standards (id, category, key, label, value_numeric, unit, display_order, is_active, created_at, updated_at)
        VALUES
          (gen_random_uuid(), 'complexity_multiplier', 'low',    '낮음 (Low)',    0.80, 'multiplier', 0, true, now(), now()),
          (gen_random_uuid(), 'complexity_multiplier', 'medium', '보통 (Medium)', 1.00, 'multiplier', 1, true, now(), now()),
          (gen_random_uuid(), 'complexity_multiplier', 'high',   '높음 (High)',   1.50, 'multiplier', 2, true, now(), now())
    """)


def downgrade() -> None:
    op.execute("DELETE FROM roi_standards")
