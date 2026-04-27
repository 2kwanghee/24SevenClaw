"""ROI 계산 및 표준 단가/공수 파라미터 스키마."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.roi_standard import RoiCategory


# ─── Admin: ROI 표준 단가 CRUD ───

class RoiStandardCreate(BaseModel):
    category: RoiCategory
    key: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    value_numeric: Decimal | None = None
    value_json: dict[str, Any] | None = None
    unit: str = Field(..., min_length=1, max_length=32)
    display_order: int = 0
    is_active: bool = True


class RoiStandardUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    value_numeric: Decimal | None = None
    value_json: dict[str, Any] | None = None
    unit: str | None = Field(None, min_length=1, max_length=32)
    display_order: int | None = None
    is_active: bool | None = None


class RoiStandardResponse(BaseModel):
    id: UUID
    category: RoiCategory
    key: str
    label: str
    description: str | None
    value_numeric: Decimal | None
    value_json: dict[str, Any] | None
    unit: str
    display_order: int
    is_active: bool
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoiStandardListResponse(BaseModel):
    items: list[RoiStandardResponse]
    total: int


# ─── Calculate: ROI 산출 ───

class RoiCalculateRequest(BaseModel):
    solution_type: str = Field(..., description="솔루션 타입 (saas, rest-api, fullstack, ...)")
    complexity: Literal["low", "medium", "high"]
    selected_agents_count: int = Field(0, ge=0)
    selected_skills_count: int = Field(0, ge=0)
    selected_hooks_count: int = Field(0, ge=0)
    platform_id: str | None = None
    overrides: dict[str, float] | None = Field(
        None,
        description="단가/공수 오버라이드 (예: {'role_rate.pm': 1200000}). 표준값을 변경하지 않음.",
    )


class RoiBreakdownItem(BaseModel):
    role_key: str
    label: str
    days: float
    rate: float
    subtotal: float


class RoiCalculateResponse(BaseModel):
    baseline_cost: float
    clickeye_cost: float
    savings: float
    savings_ratio: float
    baseline_days: float
    clickeye_days: float
    breakdown: list[RoiBreakdownItem]
    rates_snapshot: dict[str, dict[str, float]]
    formula_version: str
