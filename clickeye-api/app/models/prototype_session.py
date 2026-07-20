import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, Uuid

from app.database import Base


class PrototypeSession(Base):
    __tablename__ = "prototype_sessions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    solution_prompt = Column(Text, nullable=True)
    parsed_requirements = Column(JSON, nullable=True, default=dict)
    status = Column(String(30), nullable=False, default="pending")
    # selected_prototype_id는 prototypes와 순환 FK — use_alter로 테이블 생성 순서 문제 해소
    selected_prototype_id = Column(
        Uuid,
        ForeignKey("prototypes.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )
    selected_pm_id = Column(Uuid, ForeignKey("pm_profiles.id", ondelete="SET NULL"), nullable=True)
    current_step = Column(Integer, nullable=False, default=1)
    extra = Column("metadata", JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Prototype(Base):
    __tablename__ = "prototypes"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id = Column(
        Uuid,
        ForeignKey("prototype_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    variant_index = Column(Integer, nullable=False, default=0)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    design_pattern = Column(String(100), nullable=True)
    menu_structure = Column(JSON, nullable=True, default=dict)
    ui_structure = Column(JSON, nullable=True, default=dict)
    color_palette = Column(JSON, nullable=True, default=dict)
    thumbnail_url = Column(String(500), nullable=True)
    figma_file_key = Column(String(200), nullable=True)
    figma_embed_url = Column(String(500), nullable=True)
    status = Column(String(30), nullable=False, default="draft")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    @property
    def tech_stack_tags(self) -> list[str]:
        data = self.ui_structure or {}
        tags = data.get("tech_stack_tags", [])
        return list(tags) if isinstance(tags, list) else []

    @property
    def architecture_pattern(self) -> str | None:
        data = self.ui_structure or {}
        val = data.get("architecture_pattern")
        return str(val) if val else None

    @property
    def variant_rationale(self) -> str | None:
        data = self.ui_structure or {}
        val = data.get("variant_rationale")
        return str(val) if val else None

    @property
    def is_recommended(self) -> bool:
        data = self.ui_structure or {}
        return bool(data.get("is_recommended", False))

    @property
    def pros(self) -> list[str]:
        data = self.ui_structure or {}
        val = data.get("pros", [])
        return list(val) if isinstance(val, list) else []

    @property
    def cons(self) -> list[str]:
        data = self.ui_structure or {}
        val = data.get("cons", [])
        return list(val) if isinstance(val, list) else []

    # ── 정량 지표 (Phase A) ─────────────────────────────────────────────────
    @property
    def estimated_weeks_min(self) -> int | None:
        v = ((self.ui_structure or {}).get("estimated_weeks") or {}).get("min")
        return int(v) if isinstance(v, int | float) else None

    @property
    def estimated_weeks_max(self) -> int | None:
        v = ((self.ui_structure or {}).get("estimated_weeks") or {}).get("max")
        return int(v) if isinstance(v, int | float) else None

    @property
    def team_size_min(self) -> int | None:
        v = ((self.ui_structure or {}).get("team_size") or {}).get("min")
        return int(v) if isinstance(v, int | float) else None

    @property
    def team_size_max(self) -> int | None:
        v = ((self.ui_structure or {}).get("team_size") or {}).get("max")
        return int(v) if isinstance(v, int | float) else None

    @property
    def team_roles(self) -> list[str]:
        v = ((self.ui_structure or {}).get("team_size") or {}).get("roles", [])
        return [str(x) for x in v] if isinstance(v, list) else []

    @property
    def complexity_score(self) -> int | None:
        v = (self.ui_structure or {}).get("complexity_score")
        return int(v) if isinstance(v, int | float) else None

    @property
    def scalability_score(self) -> int | None:
        v = (self.ui_structure or {}).get("scalability_score")
        return int(v) if isinstance(v, int | float) else None

    @property
    def monthly_cost_min_usd(self) -> int | None:
        v = ((self.ui_structure or {}).get("monthly_cost_usd") or {}).get("min")
        return int(v) if isinstance(v, int | float) else None

    @property
    def monthly_cost_max_usd(self) -> int | None:
        v = ((self.ui_structure or {}).get("monthly_cost_usd") or {}).get("max")
        return int(v) if isinstance(v, int | float) else None

    @property
    def maintenance_difficulty(self) -> str | None:
        v = (self.ui_structure or {}).get("maintenance_difficulty")
        return str(v) if v else None

    @property
    def skill_requirements(self) -> list[str]:
        v = (self.ui_structure or {}).get("skill_requirements", [])
        return [str(x) for x in v] if isinstance(v, list) else []

    @property
    def match_reasoning(self) -> str | None:
        v = (self.ui_structure or {}).get("match_reasoning")
        return str(v) if v else None
