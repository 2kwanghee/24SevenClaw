"""앱 설정 테이블 추가 (prototype_variant_count, prototype_rag_top_k)

Revision ID: e8f2a3b1c4d5
Revises: d4e7a1b3c9f2
Create Date: 2026-04-21 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "e8f2a3b1c4d5"
down_revision = "d4e7a1b3c9f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", JSON, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "updated_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 초기 설정값 삽입
    op.bulk_insert(
        sa.table(
            "app_settings",
            sa.column("key", sa.String),
            sa.column("value", JSON),
            sa.column("description", sa.Text),
        ),
        [
            {
                "key": "prototype_variant_count",
                "value": {"value": 3, "min": 2, "max": 5},
                "description": "프로토타입 제안 개수 (2-5, 기본 3)",
            },
            {
                "key": "prototype_rag_top_k",
                "value": {"value": 8, "min": 1, "max": 20},
                "description": "Claude 참조용 카탈로그 top-k (1-20, 기본 8)",
            },
        ],
    )


def downgrade() -> None:
    op.drop_table("app_settings")
