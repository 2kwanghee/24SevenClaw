"""프리뷰 API 스키마 — 파일 트리 + 내용 프리뷰."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.engine.catalog import AGENTS, SKILLS

# 유효한 카탈로그 ID 집합 (엔진 카탈로그 + 데이터 카탈로그 합집합)
_VALID_AGENT_IDS = frozenset(a["id"] for a in AGENTS)
_VALID_SKILL_IDS = frozenset(s["id"] for s in SKILLS)
_VALID_PIPELINE_IDS: frozenset[str] | None = None
_VALID_DATA_AGENT_IDS: frozenset[str] | None = None
_VALID_DATA_SKILL_IDS: frozenset[str] | None = None


def _load_data_catalog() -> (
    tuple[frozenset[str], frozenset[str], frozenset[str]]
):
    """데이터 카탈로그 JSON에서 유효 ID 로드 (지연 로드)."""
    global _VALID_PIPELINE_IDS, _VALID_DATA_AGENT_IDS, _VALID_DATA_SKILL_IDS  # noqa: PLW0603
    if _VALID_PIPELINE_IDS is None:
        import json
        from pathlib import Path

        base = Path(__file__).resolve().parent.parent / "data" / "catalog"
        with (base / "pipelines.json").open() as f:
            _VALID_PIPELINE_IDS = frozenset(p["id"] for p in json.load(f))
        with (base / "agents.json").open() as f:
            _VALID_DATA_AGENT_IDS = frozenset(a["id"] for a in json.load(f))
        with (base / "skills.json").open() as f:
            _VALID_DATA_SKILL_IDS = frozenset(s["id"] for s in json.load(f))
    return _VALID_DATA_AGENT_IDS, _VALID_DATA_SKILL_IDS, _VALID_PIPELINE_IDS


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

    @field_validator("agents")
    @classmethod
    def validate_agent_ids(cls, v: list[str]) -> list[str]:
        data_agents, _, _ = _load_data_catalog()
        all_valid = _VALID_AGENT_IDS | data_agents
        invalid = [aid for aid in v if aid not in all_valid]
        if invalid:
            raise ValueError(
                f"유효하지 않은 에이전트 ID: {invalid}. "
                f"허용: {sorted(all_valid)}"
            )
        return v

    @field_validator("skills")
    @classmethod
    def validate_skill_ids(cls, v: list[str]) -> list[str]:
        _, data_skills, _ = _load_data_catalog()
        all_valid = _VALID_SKILL_IDS | data_skills
        invalid = [sid for sid in v if sid not in all_valid]
        if invalid:
            raise ValueError(
                f"유효하지 않은 스킬 ID: {invalid}. "
                f"허용: {sorted(all_valid)}"
            )
        return v

    @field_validator("pipelines")
    @classmethod
    def validate_pipeline_ids(cls, v: list[str]) -> list[str]:
        _, _, valid_pipelines = _load_data_catalog()
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
