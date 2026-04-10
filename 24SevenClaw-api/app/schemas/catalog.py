"""카탈로그 API 응답 스키마."""

from typing import Any

from pydantic import BaseModel


class CatalogResponse(BaseModel):
    """카탈로그 목록 응답."""

    items: list[dict[str, Any]]
    total: int
