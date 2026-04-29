"""프리뷰 API 스키마 — 파일 트리 + 내용 프리뷰."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

_VALID_PIPELINE_IDS: frozenset[str] | None = None


def _load_pipelines() -> frozenset[str]:
    """파이프라인 JSON에서 유효 ID 로드 (지연 로드)."""
    global _VALID_PIPELINE_IDS  # noqa: PLW0603
    if _VALID_PIPELINE_IDS is None:
        import json
        from pathlib import Path

        base = Path(__file__).resolve().parent.parent / "data" / "catalog"
        with (base / "pipelines.json").open() as f:
            _VALID_PIPELINE_IDS = frozenset(p["id"] for p in json.load(f))
    return _VALID_PIPELINE_IDS


class PreviewRequest(BaseModel):
    """프리뷰 생성 요청 — 위저드 설정 전체."""

    organization: dict[str, Any] = Field(default_factory=dict)
    solution: dict[str, Any] = Field(default_factory=dict)
    agents: list[str] = Field(
        default_factory=list,
        description="선택된 에이전트 ID 목록",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="선택된 워크플로우 ID 목록",
    )
    pipelines: list[str] = Field(
        default_factory=list,
        description="선택된 파이프라인 ID 목록",
    )
    platform: dict[str, Any] = Field(
        default_factory=dict,
        description="플랫폼 설정 (platformId 포함)",
    )
    pm_slug: str | None = Field(
        default=None,
        description="선택된 PM 프로필 slug — ZIP에 플랫폼별 PM 파일 주입",
    )

    @field_validator("pipelines")
    @classmethod
    def validate_pipeline_ids(cls, v: list[str]) -> list[str]:
        valid_pipelines = _load_pipelines()
        invalid = [pid for pid in v if pid not in valid_pipelines]
        if invalid:
            raise ValueError(
                f"유효하지 않은 파이프라인 ID: {invalid}. "
                f"허용: {sorted(valid_pipelines)}"
            )
        return v


class FileTreeNode(BaseModel):
    """파일 트리 노드."""

    path: str = Field(description="상대 경로")
    type: str = Field(
        description="file 또는 directory",
        pattern=r"^(file|directory)$",
    )
    children: list["FileTreeNode"] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    """프리뷰 생성 응답."""

    file_tree: list[FileTreeNode] = Field(description="파일 트리 구조")
    files: dict[str, str] = Field(description="파일 경로 → 내용 매핑")
