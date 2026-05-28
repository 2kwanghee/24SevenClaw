"""Registry(Agent/Skill/Hook/MCPServer) Admin CRUD 스키마."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


def localize_registry_item(item: dict[str, Any], locale: str) -> dict[str, Any]:
    """locale이 'en'이고 _en 값이 있으면 해당 값으로 덮어쓴 dict 반환 (원본 불변).

    catalog_service dict은 'label'/'label_en' 키를 사용하므로 두 패턴 모두 처리한다.
    """
    if locale != "en":
        return item
    overrides: dict[str, Any] = {}
    for field_name in ("name", "description"):
        en_val = item.get(f"{field_name}_en")
        if en_val:
            overrides[field_name] = en_val
    # catalog_service dict: label/label_en, description/description_en
    label_en = item.get("label_en")
    if label_en:
        overrides["label"] = label_en
    desc_en = item.get("description_en")
    if desc_en and "description" not in overrides:
        overrides["description"] = desc_en
    return {**item, **overrides} if overrides else item

# --- 공통 베이스 ---


class RegistryItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    name_en: str | None = Field(None, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    description_en: str | None = None
    body_md: str | None = None
    body_md_en: str | None = None
    version: str = Field(default="0.1.0", max_length=50)
    image_url: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=50)
    is_public: bool = True
    config_schema: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    compatible_pm_specialties: list[str] = Field(default_factory=list)


class RegistryItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    name_en: str | None = Field(None, max_length=200)
    description: str | None = None
    description_en: str | None = None
    body_md: str | None = None
    body_md_en: str | None = None
    version: str | None = Field(None, max_length=50)
    image_url: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=50)
    is_public: bool | None = None
    config_schema: dict[str, Any] | None = None
    tags: list[str] | None = None
    domains: list[str] | None = None
    compatible_pm_specialties: list[str] | None = None


class RegistryItemResponse(BaseModel):
    id: UUID
    name: str
    name_en: str | None = None
    slug: str
    description: str | None
    description_en: str | None = None
    body_md: str | None
    body_md_en: str | None = None
    version: str
    image_url: str | None
    category: str | None
    is_public: bool
    config_schema: dict[str, Any]
    tags: list[str]
    domains: list[str]
    compatible_pm_specialties: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegistryItemListResponse(BaseModel):
    items: list[RegistryItemResponse]
    total: int


# --- Agent ---


class AgentCreate(RegistryItemBase):
    required: bool = False
    output_file: str | None = Field(None, max_length=200)
    dependencies: list[str] = Field(default_factory=list)


class AgentUpdate(RegistryItemUpdate):
    required: bool | None = None
    output_file: str | None = Field(None, max_length=200)
    dependencies: list[str] | None = None


class AgentResponse(RegistryItemResponse):
    required: bool
    output_file: str | None
    dependencies: list[str]


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int


# --- Skill ---


class EnvVarDef(BaseModel):
    name: str
    description: str = ""
    pattern: str = ""
    required: bool = True


class SkillCreate(RegistryItemBase):
    required: bool = False
    output_file: str | None = Field(None, max_length=200)
    dependencies: list[str] = Field(default_factory=list)
    hook_events: list[str] = Field(default_factory=list)
    env_vars: list[EnvVarDef] = Field(default_factory=list)


class SkillUpdate(RegistryItemUpdate):
    required: bool | None = None
    output_file: str | None = Field(None, max_length=200)
    dependencies: list[str] | None = None
    hook_events: list[str] | None = None
    env_vars: list[EnvVarDef] | None = None


class SkillResponse(RegistryItemResponse):
    required: bool
    output_file: str | None
    dependencies: list[str]
    hook_events: list[str]
    env_vars: list[dict[str, Any]]


class SkillListResponse(BaseModel):
    items: list[SkillResponse]
    total: int


# --- Hook ---


class HookCreate(RegistryItemBase):
    # UserPromptSubmit | PreToolUse | PostToolUse | Stop
    event: str = Field(default="PostToolUse", max_length=50)
    required: bool = False
    output_file: str | None = Field(None, max_length=200)


class HookUpdate(RegistryItemUpdate):
    event: str | None = Field(None, max_length=50)
    required: bool | None = None
    output_file: str | None = Field(None, max_length=200)


class HookResponse(RegistryItemResponse):
    event: str
    required: bool
    output_file: str | None


class HookListResponse(BaseModel):
    items: list[HookResponse]
    total: int


# --- MCPServer ---


class MCPServerCreate(RegistryItemBase):
    pass


class MCPServerUpdate(RegistryItemUpdate):
    pass


class MCPServerResponse(RegistryItemResponse):
    pass
