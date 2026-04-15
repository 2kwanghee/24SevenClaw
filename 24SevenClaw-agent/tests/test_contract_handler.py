"""ContractHandler 단위 테스트."""

import json
from pathlib import Path

import pytest

from agent.config import AgentSettings
from agent.handlers.contract_handler import ContractHandler
from agent.reporter import Reporter


@pytest.fixture
def contract_handler(
    test_settings: AgentSettings,
    reporter: Reporter,
    tmp_path: Path,
) -> ContractHandler:
    """tmp_path를 data_dir로 사용하는 ContractHandler."""
    test_settings.data_dir = str(tmp_path)
    return ContractHandler(
        config=test_settings, reporter=reporter, local_store=None
    )


def _sync_payload(
    project_id: str = "proj-1",
    contracts: list[dict] | None = None,
) -> dict:
    if contracts is None:
        contracts = [
            {
                "slug": "default-settings",
                "contract_type": "settings",
                "version": "1.0.0",
                "content": {"timeout": 30, "retries": 3, "log_level": "info"},
                "overrides": {"timeout": 60},
            },
        ]
    return {"project_id": project_id, "contracts": contracts}


async def test_sync_saves_merged_file(
    contract_handler: ContractHandler,
    test_settings: AgentSettings,
) -> None:
    """계약을 머지하여 로컬 JSON 파일로 저장한다."""
    result = await contract_handler.handle(_sync_payload())

    assert result is not None
    assert result["payload"]["status"] == "completed"
    assert "default-settings" in result["payload"]["synced"]

    saved = json.loads(
        (Path(test_settings.data_dir) / "contracts" / "default-settings.json").read_text()
    )
    # override가 content에 우선 적용
    assert saved["content"]["timeout"] == 60
    assert saved["content"]["retries"] == 3


async def test_sync_multiple_contracts(
    contract_handler: ContractHandler,
    test_settings: AgentSettings,
) -> None:
    """여러 계약을 한 번에 동기화한다."""
    payload = _sync_payload(contracts=[
        {
            "slug": "skill-linter",
            "contract_type": "skill",
            "version": "2.0.0",
            "content": {"engine": "ruff", "strict": False},
            "overrides": {"strict": True},
        },
        {
            "slug": "agent-claude",
            "contract_type": "agent",
            "version": "1.1.0",
            "content": {"model": "opus", "max_tokens": 4096},
            "overrides": {},
        },
    ])

    result = await contract_handler.handle(payload)

    assert result is not None
    assert result["payload"]["status"] == "completed"
    assert len(result["payload"]["synced"]) == 2

    contracts_dir = Path(test_settings.data_dir) / "contracts"
    linter = json.loads((contracts_dir / "skill-linter.json").read_text())
    assert linter["content"]["strict"] is True

    claude = json.loads((contracts_dir / "agent-claude.json").read_text())
    assert claude["content"]["model"] == "opus"


async def test_sync_missing_project_id(contract_handler: ContractHandler) -> None:
    """project_id 누락 시 에러를 반환한다."""
    result = await contract_handler.handle({"contracts": []})

    assert result is not None
    assert result["type"] == "error"
    assert result["payload"]["code"] == "INVALID_PAYLOAD"


async def test_sync_missing_slug_skipped(
    contract_handler: ContractHandler,
) -> None:
    """slug가 빈 항목은 건너뛰고 에러로 집계한다."""
    payload = _sync_payload(contracts=[
        {
            "slug": "",
            "contract_type": "settings",
            "version": "1.0.0",
            "content": {},
            "overrides": {},
        },
        {
            "slug": "valid-one",
            "contract_type": "skill",
            "version": "1.0.0",
            "content": {"a": 1},
            "overrides": {},
        },
    ])

    result = await contract_handler.handle(payload)

    assert result is not None
    assert result["payload"]["status"] == "partial"
    assert len(result["payload"]["synced"]) == 1
    assert len(result["payload"]["errors"]) == 1


async def test_merge_override_priority() -> None:
    """_merge_contract: overrides가 content보다 우선한다."""
    item = {
        "slug": "test",
        "contract_type": "settings",
        "version": "1.0.0",
        "content": {"a": 1, "b": 2},
        "overrides": {"b": 99, "c": 3},
    }
    merged = ContractHandler._merge_contract(item)
    assert merged["content"]["a"] == 1
    assert merged["content"]["b"] == 99
    assert merged["content"]["c"] == 3
