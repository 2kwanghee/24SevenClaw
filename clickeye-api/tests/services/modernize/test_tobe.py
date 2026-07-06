"""tobe.generate_tobe_architecture 의 deterministic fallback + 영속 함수 검증.

Anthropic API key 미설정 시 LLM 호출 없이 정적 문서/갭 매트릭스가 생성되는지,
`generate_and_persist_tobe_artifacts` 가 requirements 산출물을 기반으로
tobe phase 산출물 2건(문서 + 갭 매트릭스)을 올바르게 영속하는지 검증한다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.modernize_phase_artifact import ModernizePhaseArtifact
from app.models.modernize_session import ModernizeSession
from app.models.user import User
from app.services.modernize.tobe import (
    _estimate_complexity,
    generate_and_persist_tobe_artifacts,
    generate_tobe_architecture,
)


@pytest.fixture
def no_anthropic_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "")


async def _make_user(db: AsyncSession) -> User:
    user = User(email=f"{uuid.uuid4()}@example.com", display_name="Tester")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_fallback_produces_markdown_and_gap_matrix(no_anthropic_key: None) -> None:
    tobe_md, gap_matrix, tokens_used = await generate_tobe_architecture(
        scenario="versionup",
        goals_text="",
        as_is_stack={
            "db_type": "postgresql",
            "db_version": "12",
            "runtime": "python",
            "runtime_version": "3.8",
        },
        to_be_stack={
            "db_type": "postgresql",
            "db_version": "16",
            "runtime": "python",
            "runtime_version": "3.12",
        },
        requirements_notes_md="레거시 psycopg2 → asyncpg 전환 필요",
        lang_distribution={"python": 1.0},
        framework_signals={"django": "3.2.18"},
        outdated_packages=[
            {"name": "django", "current": "3.2.18", "latest": "5.0.6", "severity": "high"},
        ],
        risk_flags=["python_eol_3_8"],
        dep_graph={"mermaid": "graph TD\n  a --> b"},
        llm_summary="",
    )

    assert tokens_used == 0
    assert "To-Be 아키텍처" in tobe_md
    assert "```mermaid" in tobe_md
    assert "graph TD" in tobe_md

    areas = {row["area"] for row in gap_matrix}
    assert "dependency" in areas
    assert "infra" in areas
    assert "database" in areas
    assert "code" in areas
    assert "test" in areas

    dep_row = next(row for row in gap_matrix if row["area"] == "dependency")
    assert dep_row["as_is"] == "django 3.2.18"
    assert dep_row["to_be"] == "django 5.0.6"
    assert dep_row["transition_type"] == "replatform"


@pytest.mark.asyncio
async def test_fallback_handles_empty_inputs(no_anthropic_key: None) -> None:
    tobe_md, gap_matrix, tokens_used = await generate_tobe_architecture(
        scenario="versionup",
        goals_text="",
        as_is_stack={},
        to_be_stack={},
        requirements_notes_md=None,
        lang_distribution={},
        framework_signals={},
        outdated_packages=[],
        risk_flags=[],
        dep_graph=None,
        llm_summary="",
    )
    assert tokens_used == 0
    assert tobe_md
    # db_type 둘 다 없으므로 database 행은 생성되지 않고, test 행만 항상 존재
    areas = [row["area"] for row in gap_matrix]
    assert areas == ["test"]


def test_estimate_complexity_thresholds() -> None:
    low = _estimate_complexity(outdated_packages=[], risk_flags=[], scenario="versionup")
    assert low < 0.7

    high = _estimate_complexity(
        outdated_packages=[{"name": f"pkg{i}"} for i in range(25)],
        risk_flags=["a", "b", "c", "d", "e"],
        scenario="language_migrate",
    )
    assert high >= 0.7


@pytest.mark.asyncio
async def test_generate_and_persist_tobe_artifacts(
    db_session: AsyncSession, no_anthropic_key: None
) -> None:
    user = await _make_user(db_session)
    session_row = ModernizeSession(
        user_id=user.id,
        repo_full_name="acme/widgets",
        scenario="versionup",
        status="ready",
        current_phase="requirements",
    )
    db_session.add(session_row)
    await db_session.commit()
    await db_session.refresh(session_row)

    requirements_artifact = ModernizePhaseArtifact(
        session_id=session_row.id,
        phase="requirements",
        artifact_type="requirements_stack",
        content_json={
            "as_is_stack": {"db_type": "postgresql", "db_version": "12"},
            "to_be_stack": {"db_type": "postgresql", "db_version": "16"},
            "notes_md": "전환 노트",
        },
    )
    db_session.add(requirements_artifact)
    await db_session.commit()
    await db_session.refresh(requirements_artifact)

    generated = await generate_and_persist_tobe_artifacts(
        db_session,
        session_row=session_row,
        requirements_artifact=requirements_artifact,
    )

    assert len(generated) == 2
    types = {a.artifact_type for a in generated}
    assert types == {"tobe_architecture", "gap_matrix"}
    for artifact in generated:
        assert artifact.phase == "tobe"
        assert artifact.session_id == session_row.id

    tobe_doc = next(a for a in generated if a.artifact_type == "tobe_architecture")
    gap_doc = next(a for a in generated if a.artifact_type == "gap_matrix")
    assert tobe_doc.content_md is not None
    assert gap_doc.content_json is not None
    assert isinstance(gap_doc.content_json["gap_matrix"], list)
