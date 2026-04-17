"""Registry(Agent/Skill/MCPServer) Admin CRUD 스키마."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# --- 공통 베이스 ---

class RegistryItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    body_md: str | None = None
    version: str = Field(default="0.1.0", max_length=50)
    image_url: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=50)
    is_public: bool = True
    config_schema: dict[str, Any] = Field(default_factory=dict)


class RegistryItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    body_md: str | None = None
    version: str | None = Field(None, max_length=50)
    image_url: str | None = Field(None, max_length=500)
    category: str | None = Field(None, max_length=50)
    is_public: bool | None = None
    config_schema: dict[str, Any] | None = None


class RegistryItemResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    body_md: str | None
    version: str
    image_url: str | None
    category: str | None
    is_public: bool
    config_schema: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RegistryItemListResponse(BaseModel):
    items: list[RegistryItemResponse]
    total: int


# --- Agent ---

class AgentCreate(RegistryItemBase):
    pass


class AgentUpdate(RegistryItemUpdate):
    pass


class AgentResponse(RegistryItemResponse):
    pass


# --- Skill ---

class SkillCreate(RegistryItemBase):
    pass


class SkillUpdate(RegistryItemUpdate):
    pass


class SkillResponse(RegistryItemResponse):
    pass


# --- MCPServer ---

class MCPServerCreate(RegistryItemBase):
    pass


class MCPServerUpdate(RegistryItemUpdate):
    pass


class MCPServerResponse(RegistryItemResponse):
    pass
