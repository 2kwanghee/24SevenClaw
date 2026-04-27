"""ROI 계산 및 표준 단가/공수 관리 서비스."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.roi_standard import RoiCategory, RoiStandard
from app.schemas.roi import (
    RoiBreakdownItem,
    RoiCalculateRequest,
    RoiCalculateResponse,
    RoiStandardCreate,
    RoiStandardUpdate,
)

FORMULA_VERSION = "v1.0"

# ClickEye 비용 계수 (baseline 대비 비율)
CLICKEYE_COST_FACTOR = 0.15
CLICKEYE_FLAT_SETUP_KRW = 2_000_000

# 컴포넌트당 추가 공수 (일/역할)
COMPONENT_EFFORT: dict[str, dict[str, float]] = {
    "agent": {"be": 0.3, "pm": 0.1},
    "skill": {"be": 0.15, "pm": 0.05},
    "hook": {"be": 0.1},
}

# solution_effort JSON 기본값 (시드에서 가져오지 못할 때 fallback)
DEFAULT_EFFORT: dict[str, dict[str, float]] = {
    "saas": {"pm": 10, "be": 20, "fe": 15, "qa": 8, "designer": 5},
    "rest-api": {"pm": 5, "be": 15, "fe": 0, "qa": 5, "designer": 0},
    "fullstack": {"pm": 12, "be": 25, "fe": 20, "qa": 10, "designer": 6},
    "internal-tool": {"pm": 5, "be": 10, "fe": 8, "qa": 4, "designer": 2},
    "mvp": {"pm": 6, "be": 12, "fe": 10, "qa": 3, "designer": 3},
    "custom": {"pm": 10, "be": 18, "fe": 12, "qa": 6, "designer": 4},
}

DEFAULT_RATES: dict[str, float] = {
    "pm": 900_000,
    "be": 1_000_000,
    "fe": 900_000,
    "qa": 600_000,
    "designer": 700_000,
}

DEFAULT_MULTIPLIERS: dict[str, float] = {
    "low": 0.8,
    "medium": 1.0,
    "high": 1.5,
}


class RoiService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ─── 표준 단가/공수 CRUD ───

    async def list_standards(self, category: RoiCategory | None = None) -> list[RoiStandard]:
        stmt = select(RoiStandard).where(RoiStandard.is_active.is_(True))
        if category:
            stmt = stmt.where(RoiStandard.category == category)
        stmt = stmt.order_by(RoiStandard.category, RoiStandard.display_order)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_standards_all(self, category: RoiCategory | None = None) -> list[RoiStandard]:
        stmt = select(RoiStandard)
        if category:
            stmt = stmt.where(RoiStandard.category == category)
        stmt = stmt.order_by(RoiStandard.category, RoiStandard.display_order)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_standard(self, standard_id: UUID) -> RoiStandard:
        item = await self.db.get(RoiStandard, standard_id)
        if not item:
            raise AppError("ROI_STANDARD_NOT_FOUND", "항목을 찾을 수 없습니다", 404)
        return item

    async def create_standard(self, data: RoiStandardCreate, updated_by: UUID) -> RoiStandard:
        existing = await self.db.execute(
            select(RoiStandard).where(
                RoiStandard.category == data.category,
                RoiStandard.key == data.key,
            )
        )
        if existing.scalar_one_or_none():
            raise AppError("ROI_STANDARD_DUPLICATE", f"'{data.category}/{data.key}' 키가 이미 존재합니다", 409)

        item = RoiStandard(**data.model_dump(), updated_by=updated_by)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_standard(self, standard_id: UUID, data: RoiStandardUpdate, updated_by: UUID) -> RoiStandard:
        item = await self.get_standard(standard_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(item, field, value)
        item.updated_by = updated_by
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def delete_standard(self, standard_id: UUID) -> None:
        item = await self.get_standard(standard_id)
        await self.db.delete(item)
        await self.db.commit()

    # ─── ROI 계산 ───

    async def calculate(self, req: RoiCalculateRequest) -> RoiCalculateResponse:
        overrides = req.overrides or {}

        # 표준 단가 로드
        role_rates = dict(DEFAULT_RATES)
        effort_by_solution: dict[str, dict[str, float]] = {k: dict(v) for k, v in DEFAULT_EFFORT.items()}
        multipliers = dict(DEFAULT_MULTIPLIERS)

        standards = await self.list_standards()
        for s in standards:
            if s.category == RoiCategory.role_rate and s.value_numeric is not None:
                role_rates[s.key] = float(s.value_numeric)
            elif s.category == RoiCategory.solution_effort and s.value_json:
                effort_by_solution[s.key] = {k: float(v) for k, v in s.value_json.items()}
            elif s.category == RoiCategory.complexity_multiplier and s.value_numeric is not None:
                multipliers[s.key] = float(s.value_numeric)

        # 오버라이드 적용 (표준 테이블은 불변)
        effective_rates = dict(role_rates)
        effective_efforts: dict[str, float] | None = None

        for key, value in overrides.items():
            prefix, _, sub_key = key.partition(".")
            if prefix == "role_rate" and sub_key:
                effective_rates[sub_key] = value
            elif prefix == "effort" and sub_key:
                if effective_efforts is None:
                    base = effort_by_solution.get(req.solution_type, DEFAULT_EFFORT.get("custom", {}))
                    effective_efforts = dict(base)
                effective_efforts[sub_key] = value

        # 기준 공수 계산
        base_effort = effort_by_solution.get(req.solution_type, DEFAULT_EFFORT.get("custom", {}))
        if effective_efforts is not None:
            base_effort = effective_efforts

        multiplier = multipliers.get(req.complexity, 1.0)

        breakdown: list[RoiBreakdownItem] = []
        total_baseline_days = 0.0
        total_baseline_cost = 0.0

        for role_key, base_days in base_effort.items():
            if base_days == 0:
                continue
            rate = effective_rates.get(role_key, DEFAULT_RATES.get(role_key, 0))
            component_extra = sum(
                COMPONENT_EFFORT.get(comp_type, {}).get(role_key, 0) * count
                for comp_type, count in [
                    ("agent", req.selected_agents_count),
                    ("skill", req.selected_skills_count),
                    ("hook", req.selected_hooks_count),
                ]
            )
            total_days = base_days * multiplier + component_extra
            subtotal = total_days * rate

            breakdown.append(RoiBreakdownItem(
                role_key=role_key,
                label=_role_label(role_key),
                days=round(total_days, 1),
                rate=rate,
                subtotal=round(subtotal, 0),
            ))
            total_baseline_days += total_days
            total_baseline_cost += subtotal

        # ClickEye 비용 (baseline 대비 15% + 고정 셋업비)
        clickeye_days = 2.0 + (req.selected_agents_count + req.selected_skills_count) * 0.1
        clickeye_cost = total_baseline_cost * CLICKEYE_COST_FACTOR + CLICKEYE_FLAT_SETUP_KRW

        savings = total_baseline_cost - clickeye_cost
        savings_ratio = savings / total_baseline_cost if total_baseline_cost > 0 else 0.0

        rates_snapshot = {
            "role_rate": dict(effective_rates),
            "complexity_multiplier": multipliers,
        }

        if req.solution_type not in effort_by_solution:
            raise AppError(
                "ROI_SOLUTION_TYPE_NOT_FOUND",
                f"솔루션 타입 '{req.solution_type}'에 대한 공수 데이터가 없습니다. 관리자에게 문의하세요.",
                422,
            )

        return RoiCalculateResponse(
            baseline_cost=round(total_baseline_cost, 0),
            clickeye_cost=round(clickeye_cost, 0),
            savings=round(savings, 0),
            savings_ratio=round(savings_ratio, 4),
            baseline_days=round(total_baseline_days, 1),
            clickeye_days=round(clickeye_days, 1),
            breakdown=breakdown,
            rates_snapshot=rates_snapshot,
            formula_version=FORMULA_VERSION,
        )


def _role_label(role_key: str) -> str:
    labels = {
        "pm": "프로젝트 매니저",
        "be": "백엔드 개발자",
        "fe": "프론트엔드 개발자",
        "qa": "QA 엔지니어",
        "designer": "UI/UX 디자이너",
    }
    return labels.get(role_key, role_key)
