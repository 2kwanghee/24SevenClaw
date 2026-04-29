"""핸들러 베이스 클래스"""

from abc import ABC, abstractmethod
from typing import Any

from agent.config import AgentSettings
from agent.reporter import Reporter


class BaseHandler(ABC):
    def __init__(
        self,
        config: AgentSettings,
        reporter: Reporter,
        local_store: Any,
    ):
        self.config = config
        self.reporter = reporter
        self.store = local_store

    @abstractmethod
    async def handle(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """명령을 처리하고 결과를 반환"""
        ...
