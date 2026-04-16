import uuid

from sqlalchemy import Column, Float, ForeignKey, Integer, Uuid

from app.database import Base


class PMMetrics(Base):
    __tablename__ = "pm_metrics"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    pm_id = Column(
        Uuid,
        ForeignKey("pm_profiles.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    usage_count = Column(Integer, nullable=False, default=0)
    completed_projects = Column(Integer, nullable=False, default=0)
    avg_rating = Column(Float, nullable=False, default=0.0)
    total_ratings = Column(Integer, nullable=False, default=0)
    success_rate = Column(Float, nullable=False, default=0.0)
    avg_completion_days = Column(Float, nullable=False, default=0.0)
