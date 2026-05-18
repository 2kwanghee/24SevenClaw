"""recommendations.generate_recommendations 의 deterministic fallback 검증.

Anthropic API key 미설정 시 outdated_packages + framework EOL 만으로
권장안이 정상 생성되는지 확인. LLM 호출 없음 — 격리 가능.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.services.modernize.recommendations import generate_recommendations


@pytest.fixture
def no_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "")


@pytest.mark.asyncio
async def test_fallback_with_outdated_packages(no_anthropic_key: None) -> None:
    recs = await generate_recommendations(
        scenario="versionup",
        goals_text="",
        lang_distribution={"python": 1.0},
        framework_signals={"django": "3.2.18"},
        outdated_packages=[
            {
                "name": "django",
                "current": "3.2.18",
                "latest": "5.0.6",
                "kind": "python",
                "severity": "high",
            },
            {
                "name": "psycopg",
                "current": "2.9.5",
                "latest": "3.1.0",
                "kind": "python",
                "severity": "med",
            },
        ],
        manifests=[],
        llm_summary="",
    )
    assert len(recs) == 2
    # 첫 권장안: django, severity high
    assert recs[0]["category"] == "upgrade"
    assert recs[0]["before"]["pkg"] == "django"
    assert recs[0]["after"]["version"] == "5.0.6"
    assert recs[0]["risk"] == "high"
    assert recs[0]["effort"] == "L"


@pytest.mark.asyncio
async def test_fallback_eol_python_added_even_without_outdated(
    no_anthropic_key: None,
) -> None:
    recs = await generate_recommendations(
        scenario="versionup",
        goals_text="",
        lang_distribution={"python": 1.0},
        framework_signals={"python": "3.8"},
        outdated_packages=[],
        manifests=[],
        llm_summary="",
    )
    # outdated 가 비어있어도 python EOL 권장안 1건 자동 추가
    assert len(recs) == 1
    assert "python" in recs[0]["title"].lower()
    assert recs[0]["risk"] == "high"
    assert recs[0]["priority"] == 1  # EOL 은 최우선


@pytest.mark.asyncio
async def test_fallback_prompt_md_includes_title(no_anthropic_key: None) -> None:
    recs = await generate_recommendations(
        scenario="versionup",
        goals_text="",
        lang_distribution={"node": 1.0},
        framework_signals={},
        outdated_packages=[
            {
                "name": "react",
                "current": "16.0.0",
                "latest": "19.0.0",
                "kind": "node",
                "severity": "high",
            },
        ],
        manifests=[],
        llm_summary="",
    )
    assert "react" in recs[0]["prompt_md"]
    assert "16.0.0" in recs[0]["prompt_md"]
    assert "19.0.0" in recs[0]["prompt_md"]


@pytest.mark.asyncio
async def test_fallback_handles_empty_inputs(no_anthropic_key: None) -> None:
    recs = await generate_recommendations(
        scenario="versionup",
        goals_text="",
        lang_distribution={},
        framework_signals={},
        outdated_packages=[],
        manifests=[],
        llm_summary="",
    )
    assert recs == []


@pytest.mark.asyncio
async def test_fallback_priority_ordering(no_anthropic_key: None) -> None:
    """high severity 가 low 보다 priority 가 낮게 (= 먼저)."""
    recs = await generate_recommendations(
        scenario="versionup",
        goals_text="",
        lang_distribution={"python": 1.0},
        framework_signals={},
        outdated_packages=[
            {
                "name": "a-low",
                "current": "1.0",
                "latest": "1.1",
                "kind": "python",
                "severity": "low",
            },
            {
                "name": "b-high",
                "current": "2.0",
                "latest": "3.0",
                "kind": "python",
                "severity": "high",
            },
        ],
        manifests=[],
        llm_summary="",
    )
    assert len(recs) == 2
    high_rec = next(r for r in recs if r["before"]["pkg"] == "b-high")
    low_rec = next(r for r in recs if r["before"]["pkg"] == "a-low")
    assert high_rec["priority"] < low_rec["priority"]
