"""카탈로그 API 응답 스키마."""

from typing import Any

from pydantic import BaseModel


class CatalogItemResponse(BaseModel):
    """카탈로그 아이템 응답 — id, label, description 필수."""

    id: str
    label: str
    description: str | None = None
    category: str | None = None


class CatalogListResponse(BaseModel):
    """에이전트/스킬 카탈로그 목록 응답 (스키마 검증 포함)."""

    items: list[CatalogItemResponse]
    total: int


class CatalogResponse(BaseModel):
    """범용 카탈로그 목록 응답 (platforms, pipelines 등)."""

    items: list[dict[str, Any]]
    total: int
