"""ConfigHandler 단위 테스트."""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from agent.config import AgentSettings
from agent.handlers.config_handler import ConfigHandler
from agent.local_store import LocalStore
from agent.reporter import Reporter


@pytest.fixture
async def tmp_store(tmp_path: Path) -> LocalStore:
    """임시 SQLite 기반 LocalStore."""
    db_path = str(tmp_path / "test.db")
    store = LocalStore(db_path=db_path)
    await store.init()
    yield store  # type: ignore[misc]
    await store.close()


@pytest.fixture
def config_handler(
    test_settings: AgentSettings,
    reporter: Reporter,
    tmp_store: LocalStore,
) -> ConfigHandler:
    """테스트용 ConfigHandler."""
    return ConfigHandler(
        config=test_settings,
        reporter=reporter,
        local_store=tmp_store,
    )


def _make_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "preset_id": "preset-uuid-001",
        "preset_slug": "advanced-fullstack",
        "agents": ["claude-code", "gemini-cli"],
        "skills": ["tdd", "lint"],
        "pipelines": ["ci-basic"],
        "metadata": {"version": "1.0"},
    }
    base.update(overrides)
    return base


# ── 정상 처리 ────────────────────────────────────────────

async def test_handle_saves_preset_id(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    payload = _make_payload()
    await config_handler.handle(payload)

    stored_id = await tmp_store.get_config("preset.active_id")
    assert stored_id == "preset-uuid-001"


async def test_handle_saves_preset_slug(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    payload = _make_payload()
    await config_handler.handle(payload)

    stored_slug = await tmp_store.get_config("preset.active_slug")
    assert stored_slug == "advanced-fullstack"


async def test_handle_saves_agents(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    payload = _make_payload()
    await config_handler.handle(payload)

    agents = await tmp_store.get_config("preset.agents")
    assert agents == ["claude-code", "gemini-cli"]


async def test_handle_saves_skills(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    payload = _make_payload()
    await config_handler.handle(payload)

    skills = await tmp_store.get_config("preset.skills")
    assert skills == ["tdd", "lint"]


async def test_handle_saves_pipelines(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    payload = _make_payload()
    await config_handler.handle(payload)

    pipelines = await tmp_store.get_config("preset.pipelines")
    assert pipelines == ["ci-basic"]


async def test_handle_saves_metadata(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    payload = _make_payload()
    await config_handler.handle(payload)

    metadata = await tmp_store.get_config("preset.metadata")
    assert metadata == {"version": "1.0"}


async def test_handle_saves_raw_payload(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    payload = _make_payload()
    await config_handler.handle(payload)

    raw = await tmp_store.get_config("preset.raw")
    assert raw["preset_id"] == "preset-uuid-001"
    assert raw["agents"] == ["claude-code", "gemini-cli"]


async def test_handle_returns_success_result(config_handler: ConfigHandler) -> None:
    payload = _make_payload()
    result = await config_handler.handle(payload)

    assert result is not None
    assert result["type"] == "agent.result"
    assert result["payload"]["status"] == "completed"
    assert "advanced-fullstack" in result["payload"]["summary"]


# ── 리로드 시그널 ────────────────────────────────────────

async def test_handle_sets_reload_event(config_handler: ConfigHandler) -> None:
    assert not config_handler.reload_event.is_set()

    await config_handler.handle(_make_payload())

    assert config_handler.reload_event.is_set()


async def test_custom_reload_event() -> None:
    """외부에서 주입한 reload_event도 동작한다."""
    event = asyncio.Event()
    store = LocalStore(db_path=":memory:")
    await store.init()
    try:
        handler = ConfigHandler(
            config=AgentSettings(),
            reporter=Reporter(connection=AsyncMock()),
            local_store=store,
            reload_event=event,
        )
        await handler.handle(_make_payload())
        assert event.is_set()
    finally:
        await store.close()


# ── 부분 payload ─────────────────────────────────────────

async def test_handle_partial_payload(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    """agents만 포함된 부분 payload도 정상 처리."""
    payload = {
        "preset_id": "partial-001",
        "preset_slug": "minimal",
        "agents": ["claude-code"],
    }
    result = await config_handler.handle(payload)

    assert result is not None
    assert result["payload"]["status"] == "completed"

    agents = await tmp_store.get_config("preset.agents")
    assert agents == ["claude-code"]

    # 누락된 키는 저장되지 않음
    skills = await tmp_store.get_config("preset.skills")
    assert skills is None


# ── 덮어쓰기 ─────────────────────────────────────────────

async def test_handle_overwrites_previous(
    config_handler: ConfigHandler, tmp_store: LocalStore
) -> None:
    """두 번 호출하면 최신 값으로 덮어쓴다."""
    await config_handler.handle(_make_payload(preset_slug="v1", agents=["a"]))
    await config_handler.handle(_make_payload(preset_slug="v2", agents=["b", "c"]))

    slug = await tmp_store.get_config("preset.active_slug")
    agents = await tmp_store.get_config("preset.agents")
    assert slug == "v2"
    assert agents == ["b", "c"]
