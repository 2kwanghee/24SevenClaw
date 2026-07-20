"""user_anthropic_credentials에_credential_type_추가_및_UNIQUE_제약_변경

Revision ID: 473eddce9fcb
Revises: ec1c76eb9044
Create Date: 2026-05-09 14:21:42.342277
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic
revision: str = "473eddce9fcb"
down_revision: str | None = "ec1c76eb9044"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # credential_type 컬럼 추가 (기존 row는 'api_key'로 백필)
    op.add_column(
        "user_anthropic_credentials",
        sa.Column(
            "credential_type",
            sa.String(32),
            nullable=False,
            server_default="api_key",
        ),
    )

    # 기존 user_id 단일 UNIQUE 제약 제거
    op.drop_constraint(
        "user_anthropic_credentials_user_id_key",
        "user_anthropic_credentials",
        type_="unique",
    )

    # (user_id, credential_type) 복합 UNIQUE 추가
    op.create_unique_constraint(
        "uq_user_credential_type",
        "user_anthropic_credentials",
        ["user_id", "credential_type"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_credential_type", "user_anthropic_credentials", type_="unique")
    op.create_unique_constraint(
        "user_anthropic_credentials_user_id_key",
        "user_anthropic_credentials",
        ["user_id"],
    )
    op.drop_column("user_anthropic_credentials", "credential_type")
