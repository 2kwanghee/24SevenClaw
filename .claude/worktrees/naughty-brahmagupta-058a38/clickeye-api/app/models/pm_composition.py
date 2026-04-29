import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Uuid,
)

from app.database import Base


class PMComposition(Base):
    __tablename__ = "pm_compositions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    pm_id = Column(
        Uuid, ForeignKey("pm_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_type = Column(String(100), nullable=False)   # "agent" | "skill" | "tool"
    component_slug = Column(String(100), nullable=False)
    component_name = Column(String(200), nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    display_order = Column(Integer, nullable=False, default=0)
    is_required = Column(Boolean, nullable=False, default=False)
