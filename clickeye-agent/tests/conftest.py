"""Agent 테스트 공통 fixture."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from agent.config import AgentSettings
from agent.dispatcher import Dispatcher
from agent.reporter import Reporter


@pytest.fixture
def test_settings() -> AgentSettings:
    """테스트용 Agent 설정."""
    return AgentSettings(
        agent_id="test-agent-001",
        agent_secret="test-secret",
        license_key="test-license",
        cloud_ws_url="ws://localhost:9999",
        heartbeat_interval=1,
        data_dir="/tmp/sevenclaw-test",
        local_db_path="/tmp/sevenclaw-test/agent.db",
    )


@pytest.fixture
def mock_connection() -> AsyncMock:
    """Mock CloudConnection."""
    conn = AsyncMock()
    conn.send = AsyncMock()
    return conn


@pytest.fixture
def reporter(mock_connection: AsyncMock) -> Reporter:
    """테스트용 Reporter."""
    return Reporter(connection=mock_connection)


@pytest.fixture
def dispatcher() -> Dispatcher:
    """테스트용 Dispatcher."""
    return Dispatcher()


class StubHandler:
    """테스트용 스텁 핸들러."""

    def __init__(self, result: dict[str, Any] | None = None):
        self.result = result
        self.called_with: dict[str, Any] | None = None

    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        self.called_with = payload
        return self.result
