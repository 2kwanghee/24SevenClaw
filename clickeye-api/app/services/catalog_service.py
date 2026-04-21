"""카탈로그 JSON 파일 로딩 및 캐싱 서비스."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "catalog"

CATALOG_TYPES = ("agents", "skills", "platforms", "pipelines")


@lru_cache(maxsize=4)
def _load_json(catalog_type: str) -> list[dict[str, Any]]:
    """JSON 파일을 읽고 캐싱한다."""
    file_path = DATA_DIR / f"{catalog_type}.json"
    with file_path.open(encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)
    return data


class CatalogService:
    """카탈로그 데이터 조회 서비스."""

    def get(self, catalog_type: str) -> list[dict[str, Any]]:
        """카탈로그 타입별 데이터를 반환한다."""
        if catalog_type not in CATALOG_TYPES:
            msg = f"지원하지 않는 카탈로그 타입: {catalog_type}"
            raise ValueError(msg)
        return _load_json(catalog_type)
