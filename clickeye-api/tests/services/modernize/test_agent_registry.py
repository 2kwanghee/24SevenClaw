"""agent_registry 단위 테스트 — 레지스트리 스키마 검증 + 태그 도출 + 팩 조회.

외부 의존 X, 순수 함수 테스트.
"""

from __future__ import annotations

from app.services.modernize.agent_registry import (
    _TAG_PRIORITY,
    derive_requirement_tags,
    load_registry,
    resolve_pack,
)

_DB_COMBOS = (
    "mariadb->postgresql",
    "mysql->postgresql",
    "mssql->postgresql",
    "oracle->postgresql",
)


def test_registry_loads_and_validates() -> None:
    registry = load_registry()
    for tag in _TAG_PRIORITY:
        assert tag in registry.packs, f"태그 {tag} 에 대응하는 팩이 레지스트리에 없습니다"


def test_registry_every_pack_has_agent_and_skill() -> None:
    registry = load_registry()
    for tag, pack in registry.packs.items():
        assert pack.agents, f"{tag} 팩에 agents 가 비어있습니다"
        assert pack.skills, f"{tag} 팩에 skills 가 비어있습니다"


def test_db_migrate_pack_covers_required_combos() -> None:
    registry = load_registry()
    db_pack = registry.packs["db_migrate"]
    for combo_key in _DB_COMBOS:
        assert combo_key in db_pack.combos, f"db_migrate 팩에 {combo_key} 콤보가 없습니다"
        combo = db_pack.combos[combo_key]
        assert combo.task_sequence, f"{combo_key} 콤보에 task_sequence 가 비어있습니다"
        assert combo.notes_md.strip()
    assert "generic" in db_pack.combos


def test_db_migrate_pack_has_db_migrator_agent() -> None:
    registry = load_registry()
    assert "db-migrator" in registry.packs["db_migrate"].agents


def test_derive_requirement_tags_db_migrate() -> None:
    tags = derive_requirement_tags(
        scenario="language_migrate",
        as_is_db="mariadb",
        to_be={"db_type": "postgresql"},
        goals_text="DB를 PostgreSQL로 이관하고 싶습니다",
    )
    assert "db_migrate" in tags
    # language_migrate 도 scenario 로부터 함께 감지됨 — 우선순위상 db_migrate 보다 먼저
    assert tags[0] == "language_migrate"
    assert "db_migrate" in tags


def test_derive_requirement_tags_same_db_no_migrate() -> None:
    tags = derive_requirement_tags(
        scenario="versionup",
        as_is_db="postgresql",
        to_be={"db_type": "postgresql"},
        goals_text=None,
    )
    assert "db_migrate" not in tags
    assert "versionup" in tags


def test_derive_requirement_tags_defaults_to_refactor() -> None:
    tags = derive_requirement_tags(scenario=None, as_is_db=None, to_be=None, goals_text=None)
    assert tags == ["refactor"]


def test_derive_requirement_tags_refactor_keyword() -> None:
    tags = derive_requirement_tags(
        scenario="versionup", as_is_db=None, to_be=None, goals_text="기술부채를 리팩터링하고 싶어요"
    )
    assert "refactor" in tags
    assert "versionup" in tags


def test_resolve_pack_mariadb_to_postgresql_combo() -> None:
    resolved = resolve_pack(["db_migrate"], source_db="mariadb", target_db="postgresql")
    assert resolved.primary_agent == "db-migrator"
    assert "db-migrator" in resolved.agents
    assert resolved.combo is not None
    assert resolved.combo_key == "mariadb->postgresql"
    assert resolved.combo.task_sequence
    assert "AUTO_INCREMENT" in resolved.combo.notes_md


def test_resolve_pack_unknown_combo_falls_back_to_generic() -> None:
    resolved = resolve_pack(["db_migrate"], source_db="sqlite", target_db="mongodb")
    assert resolved.combo is not None
    assert resolved.combo_key == "sqlite->mongodb"
    # generic fallback 은 sqlite->mongodb 콤보가 없을 때 사용됨
    registry = load_registry()
    assert "sqlite->mongodb" not in registry.packs["db_migrate"].combos


def test_resolve_pack_merges_multiple_tags_preserving_priority() -> None:
    resolved = resolve_pack(["versionup", "db_migrate"], source_db="mysql", target_db="postgresql")
    assert resolved.tags == ["db_migrate", "versionup"]
    assert resolved.primary_agent == "db-migrator"
    assert "db-migrator" in resolved.agents
    assert "dependency-upgrader" in resolved.agents


def test_resolve_pack_no_tags_returns_empty() -> None:
    resolved = resolve_pack([])
    assert resolved.agents == []
    assert resolved.skills == []
    assert resolved.primary_agent is None
