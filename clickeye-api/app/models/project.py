from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text, Uuid, text

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Project(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    owner_id = Column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    settings = Column(JSON, nullable=False, default=dict)
    wizard_data = Column(JSON, nullable=True)
    prototype_session_id = Column(
        Uuid,
        ForeignKey("prototype_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    pm_profile_id = Column(
        Uuid,
        ForeignKey("pm_profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    project_type = Column(
        String(30), nullable=True, default="legacy", server_default=text("'legacy'")
    )
    initial_task_url = Column(String(500), nullable=True)
    # 컨트롤 타워: 고객사 직접 연결 (SET NULL on org delete)
    organization_id = Column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # 부트스트랩: 위저드 요구사항 → 로컬 분해 → Linear 자동 등록
    requirements_text = Column(Text, nullable=True)
    setup_token_hash = Column(String(128), nullable=True)
    bootstrap_status = Column(
        String(32), nullable=False, default="skipped", server_default=text("'skipped'")
    )
    bootstrap_completed_at = Column(DateTime(timezone=True), nullable=True)
