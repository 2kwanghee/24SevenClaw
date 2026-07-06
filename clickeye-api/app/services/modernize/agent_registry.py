"""요구사항 태그 → 에이전트/스킬/태스크템플릿 매핑 레지스트리.

`app/data/modernize/agent_pack_registry.json` 을 SSOT 로 삼아, 세션의 시나리오/목표/
as-is·to-be 스택으로부터 요구사항 태그를 도출하고(`derive_requirement_tags`), 태그에 맞는
에이전트 팩을 조회한다(`resolve_pack`). DB 마이그레이션 태그는 소스→타깃 DB 조합별 전용
주의사항/태스크 시퀀스를 추가로 제공한다.

계산된 requirement_tags 는 plan_builder.build_plan() 의 assigned_agent 산출과
zip_builder 의 `.claude/agents/*.md` / `.claude/skills/*.md` 번들 선택의 입력이 된다.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

RequirementTag = Literal[
    "language_migrate", "db_migrate", "replatform", "versionup", "refactor"
]

# 우선순위 순서 — 여러 태그가 동시에 감지될 때 primary agent 선택 및 표시 순서에 사용.
_TAG_PRIORITY: tuple[RequirementTag, ...] = (
    "language_migrate",
    "db_migrate",
    "replatform",
    "versionup",
    "refactor",
)

# 'migrate' 태스크의 대표 에이전트 선택 우선순위 — db_migrate 가 language_migrate 보다 구체적
_AGENT_SELECTION_PRIORITY: tuple[RequirementTag, ...] = (
    "db_migrate",
    "language_migrate",
    "replatform",
    "versionup",
    "refactor",
)

_DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "modernize" / (
    "agent_pack_registry.json"
)

_REFACTOR_KEYWORDS = ("리팩터", "리팩토링", "refactor", "기술부채", "클린업", "cleanup")


class DbMigrationCombo(BaseModel):
    """DB 마이그레이션 태그의 소스→타깃 조합별 지식."""

    notes_md: str = ""
    task_sequence: list[str] = Field(default_factory=list)


class AgentPackDefinition(BaseModel):
    """요구사항 태그 1개에 대응하는 에이전트 팩 정의."""

    description: str = ""
    agents: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    task_templates: list[str] = Field(default_factory=list)
    preflight_checks: list[str] = Field(default_factory=list)
    combos: dict[str, DbMigrationCombo] = Field(default_factory=dict)


class AgentPackRegistry(BaseModel):
    """전체 레지스트리 — 태그 → 팩 정의."""

    packs: dict[str, AgentPackDefinition]


class ResolvedPack:
    """태그 목록에 대해 병합·중복제거 된 결과. 여러 태그의 팩을 태그 우선순위 순으로 병합한다."""

    def __init__(
        self,
        *,
        tags: list[str],
        packs_by_tag: dict[str, AgentPackDefinition],
        combo: DbMigrationCombo | None = None,
        combo_key: str | None = None,
    ) -> None:
        self.tags = tags
        self.packs_by_tag = packs_by_tag
        self.combo = combo
        self.combo_key = combo_key

    @property
    def agents(self) -> list[str]:
        return _dedup_flatten(self.packs_by_tag[t].agents for t in self.tags)

    @property
    def skills(self) -> list[str]:
        return _dedup_flatten(self.packs_by_tag[t].skills for t in self.tags)

    @property
    def preflight_checks(self) -> list[str]:
        return _dedup_flatten(self.packs_by_tag[t].preflight_checks for t in self.tags)

    @property
    def primary_agent(self) -> str | None:
        """'migrate' 카테고리 태스크에 배정할 대표 에이전트.

        `_TAG_PRIORITY`(태그 표시 순서: language_migrate 우선)와 달리, 여기서는 db_migrate 가
        language_migrate 보다 우선한다 — 두 태그가 동시에 감지돼도(예: 언어 이관 중 DB 도 함께
        바뀌는 경우) 실제 스키마/데이터 이관을 수행하는 db-migrator 가 더 구체적인 지식을 갖는다.
        """
        for tag in _AGENT_SELECTION_PRIORITY:
            pack = self.packs_by_tag.get(tag)
            if pack and pack.agents:
                return pack.agents[0]
        return None

    def task_templates_for(self, tag: str) -> list[str]:
        pack = self.packs_by_tag.get(tag)
        return list(pack.task_templates) if pack else []

    def description_for(self, tag: str) -> str:
        pack = self.packs_by_tag.get(tag)
        return pack.description if pack else ""


def _dedup_flatten(lists: Any) -> list[str]:
    seen: list[str] = []
    for lst in lists:
        for item in lst:
            if item not in seen:
                seen.append(item)
    return seen


@lru_cache(maxsize=1)
def load_registry() -> AgentPackRegistry:
    """`agent_pack_registry.json` 을 읽고 Pydantic 스키마로 검증해 반환. 프로세스 내 캐시."""
    with _DATA_PATH.open(encoding="utf-8") as f:
        raw = json.load(f)
    return AgentPackRegistry(packs=raw)


def normalize_db_type(value: str | None) -> str | None:
    """DB 종류 문자열을 소문자/공백제거. 빈 값이면 None."""
    if not value or not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    return normalized or None


def derive_requirement_tags(
    *,
    scenario: str | None,
    as_is_db: str | None,
    to_be: dict[str, Any] | None,
    goals_text: str | None,
) -> list[str]:
    """세션 정보로부터 요구사항 태그를 도출.

    Phase 2(CE-285, 미병합)가 as_is/to_be StackDescriptor 전체를 비교하는 것과 달리,
    현재 살아있는 7-step 파이프라인에서 실제로 구할 수 있는 값(scenario/target_stack/
    as-is 스캔에서 감지한 db_type)만으로 최소 구현한다. Phase 2 병합 시 재조정 필요.
    """
    to_be = to_be or {}
    tags: set[str] = set()

    as_is_db_n = normalize_db_type(as_is_db)
    to_be_db_n = normalize_db_type(to_be.get("db_type") or to_be.get("db"))
    if as_is_db_n and to_be_db_n and as_is_db_n != to_be_db_n:
        tags.add("db_migrate")

    if scenario == "language_migrate":
        tags.add("language_migrate")

    to_be_infra = to_be.get("infra")
    if isinstance(to_be_infra, str) and to_be_infra.strip():
        tags.add("replatform")

    if scenario == "versionup":
        tags.add("versionup")

    goals_lower = (goals_text or "").lower()
    if any(k in goals_lower for k in _REFACTOR_KEYWORDS) or scenario == "refactor":
        tags.add("refactor")

    ordered: list[str] = [tag for tag in _TAG_PRIORITY if tag in tags]
    return ordered or ["refactor"]


def resolve_pack(
    tags: list[str],
    *,
    source_db: str | None = None,
    target_db: str | None = None,
    registry: AgentPackRegistry | None = None,
) -> ResolvedPack:
    """태그 목록 → 병합된 에이전트 팩. db_migrate 태그가 있으면 조합별 콤보를 함께 조회."""
    registry = registry or load_registry()
    ordered_tags: list[str] = [tag for tag in _TAG_PRIORITY if tag in tags]
    packs_by_tag: dict[str, AgentPackDefinition] = {
        tag: registry.packs[tag] for tag in ordered_tags if tag in registry.packs
    }

    combo: DbMigrationCombo | None = None
    combo_key: str | None = None
    db_pack = packs_by_tag.get("db_migrate")
    if db_pack is not None:
        src = normalize_db_type(source_db) or "generic"
        dst = normalize_db_type(target_db) or "generic"
        combo_key = f"{src}->{dst}"
        combo = db_pack.combos.get(combo_key) or db_pack.combos.get("generic")

    return ResolvedPack(
        tags=ordered_tags, packs_by_tag=packs_by_tag, combo=combo, combo_key=combo_key
    )
