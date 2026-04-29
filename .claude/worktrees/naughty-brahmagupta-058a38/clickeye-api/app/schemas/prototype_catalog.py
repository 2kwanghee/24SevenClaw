"""프로토타입 카탈로그 Pydantic 스키마."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── PrototypeCatalogEntry ─────────────────────────────────────────────────────

class PrototypeCatalogEntryBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None

    tags: list[str] = Field(default_factory=list)
    primary_tag: str | None = Field(None, max_length=100)

    design_pattern: str | None = Field(None, max_length=100)
    architecture_pattern: str | None = Field(None, max_length=200)
    tech_stack_tags: list[str] = Field(default_factory=list)

    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    ui_structure: dict[str, Any] = Field(default_factory=dict)
    menu_structure: dict[str, Any] = Field(default_factory=dict)
    color_palette: dict[str, Any] = Field(default_factory=dict)

    design_philosophy: str | None = None
    implementation_constraints: list[str] = Field(default_factory=list)
    recommended_agents: list[str] = Field(default_factory=list)
    optional_agents: list[str] = Field(default_factory=list)
    excluded_agents: list[str] = Field(default_factory=list)
    recommended_skills: list[str] = Field(default_factory=list)
    agent_strategy: str | None = None
    task_distribution_guide: str | None = None

    is_active: bool = True
    priority: int = 0


class PrototypeCatalogEntryCreate(PrototypeCatalogEntryBase):
    pass


class PrototypeCatalogEntryUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=300)
    description: str | None = None

    tags: list[str] | None = None
    primary_tag: str | None = Field(None, max_length=100)

    design_pattern: str | None = Field(None, max_length=100)
    architecture_pattern: str | None = Field(None, max_length=200)
    tech_stack_tags: list[str] | None = None

    pros: list[str] | None = None
    cons: list[str] | None = None
    ui_structure: dict[str, Any] | None = None
    menu_structure: dict[str, Any] | None = None
    color_palette: dict[str, Any] | None = None

    design_philosophy: str | None = None
    implementation_constraints: list[str] | None = None
    recommended_agents: list[str] | None = None
    optional_agents: list[str] | None = None
    excluded_agents: list[str] | None = None
    recommended_skills: list[str] | None = None
    agent_strategy: str | None = None
    task_distribution_guide: str | None = None

    is_active: bool | None = None
    priority: int | None = None


class PrototypeCatalogEntryResponse(PrototypeCatalogEntryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PrototypeCatalogListResponse(BaseModel):
    items: list[PrototypeCatalogEntryResponse]
    total: int


# ── PrototypeTag ──────────────────────────────────────────────────────────────

class PrototypeTagBase(BaseModel):
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    label: str = Field(..., min_length=1, max_length=100)
    label_ko: str | None = Field(None, max_length=100)
    description: str | None = None
    color: str | None = Field(None, max_length=20)
    is_active: bool = True
    sort_order: int = 0


class PrototypeTagCreate(PrototypeTagBase):
    pass


class PrototypeTagUpdate(BaseModel):
    label: str | None = Field(None, min_length=1, max_length=100)
    label_ko: str | None = Field(None, max_length=100)
    description: str | None = None
    color: str | None = Field(None, max_length=20)
    is_active: bool | None = None
    sort_order: int | None = None


class PrototypeTagResponse(PrototypeTagBase):
    id: UUID

    model_config = {"from_attributes": True}


class PrototypeTagListResponse(BaseModel):
    items: list[PrototypeTagResponse]
    total: int
