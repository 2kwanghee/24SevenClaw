"""zip_builder.generate_modernize_zip 단위 테스트 — ZIP 트리 구조 검증.

R-2 회귀 검증의 핵심 — 동일 입력 → 동일 ZIP 트리 (시그니처는 변하지 않아야).
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from app.services.modernize.zip_builder import generate_modernize_zip

_BASE_KWARGS: dict[str, Any] = {
    "repo_full_name": "acme/api",
    "scenario": "versionup",
    "session_id": "session-uuid-123",
    "llm_summary_md": "# 진단 요약\n\n- python: 3.8 EOL",
    "analysis_data": {
        "lang_distribution": {"python": 1.0},
        "framework_signals": {"python": "3.8"},
        "outdated_packages": [],
        "risk_flags": ["python_eol_3_8"],
    },
    "recommendations": [
        {
            "id": "rec-1",
            "linear_identifier": "CE-101",
            "title": "Python 3.8 → 3.12",
            "rationale_md": "EOL 대응",
            "prompt_md": "# Upgrade Python\n\nAcceptance: ...",
            "target_path": "pyproject.toml",
            "risk": "high",
            "effort": "L",
            "category": "upgrade",
        },
    ],
    "linear_team_id": "team-uuid",
    "linear_issues": [
        {"rec_id": "rec-1", "linear_identifier": "CE-101", "title": "Python 3.8 → 3.12"}
    ],
}


def _open(zip_bytes: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(zip_bytes), "r")


def test_zip_tree_has_required_files() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        names = set(zf.namelist())
    assert ".clickeye/linear-issues.json" in names
    assert ".ralph/tasks/CE-101.md" in names
    assert "docs/diagnosis.md" in names
    assert "docs/diagnosis.json" in names
    assert "MODERNIZE_README.md" in names
    assert ".env.example" in names


def test_zip_tree_has_local_execution_pack() -> None:
    """R1 — `.claude/` 에이전트·스킬·룰 + `docs/modernize/` 단계 산출물."""
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        names = set(zf.namelist())

    assert ".claude/CLAUDE.md" in names
    for slug in (
        "modernize-pm",
        "asis-analyzer",
        "code-migrator",
        "db-migrator",
        "test-guardian",
        "work-recorder",
    ):
        assert f".claude/agents/{slug}.md" in names
    for slug in ("modernize-phase-runner", "migration-verify", "record-work"):
        assert f".claude/skills/{slug}/SKILL.md" in names
    for doc in (
        "requirements.md",
        "tobe-architecture.md",
        "modernization-plan.md",
        "preflight-review.md",
        "plan.json",
    ):
        assert f"docs/modernize/{doc}" in names


def test_zip_agents_and_skills_have_recognizable_frontmatter() -> None:
    """Claude Code 가 서브에이전트/스킬로 인식하려면 YAML frontmatter(name/description) 필요."""
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        for slug in (
            "modernize-pm",
            "asis-analyzer",
            "code-migrator",
            "db-migrator",
            "test-guardian",
            "work-recorder",
        ):
            body = zf.read(f".claude/agents/{slug}.md").decode("utf-8")
            assert body.startswith("---\n")
            assert f"name: {slug}" in body
            assert "description:" in body
        for slug in ("modernize-phase-runner", "migration-verify", "record-work"):
            body = zf.read(f".claude/skills/{slug}/SKILL.md").decode("utf-8")
            assert body.startswith("---\n")
            assert f"name: {slug}" in body
            assert "description:" in body


def test_zip_claude_md_renders_session_context() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        claude_md = zf.read(".claude/CLAUDE.md").decode("utf-8")
        pm_md = zf.read(".claude/agents/modernize-pm.md").decode("utf-8")
    assert "acme/api" in claude_md
    assert "session-uuid-123" in claude_md
    assert "acme/api" in pm_md


def test_zip_phase_docs_fallback_when_no_artifacts() -> None:
    """phase_artifacts 미전달 시 각 단계 문서는 승인 전 플레이스홀더로 폴백."""
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        requirements_md = zf.read("docs/modernize/requirements.md").decode("utf-8")
        plan_json = json.loads(zf.read("docs/modernize/plan.json"))
    assert "아직 승인된" in requirements_md
    assert plan_json == {}


def test_zip_phase_docs_render_approved_artifacts() -> None:
    kwargs = {
        **_BASE_KWARGS,
        "phase_artifacts": [
            {
                "phase": "requirements",
                "artifact_type": "requirements_stack",
                "content_md": "# 요구사항\n\npostgresql 12 -> 16",
                "content_json": None,
            },
            {
                "phase": "plan",
                "artifact_type": "plan_summary",
                "content_md": "# 계획\n\n단계별 작업 목록",
                "content_json": {"tasks": ["CE-101"]},
            },
        ],
    }
    data = generate_modernize_zip(**kwargs)
    with _open(data) as zf:
        requirements_md = zf.read("docs/modernize/requirements.md").decode("utf-8")
        plan_md = zf.read("docs/modernize/modernization-plan.md").decode("utf-8")
        plan_json = json.loads(zf.read("docs/modernize/plan.json"))
    assert "postgresql 12 -> 16" in requirements_md
    assert "단계별 작업 목록" in plan_md
    assert plan_json == {"tasks": ["CE-101"]}


def test_zip_linear_issues_json_content() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        content = json.loads(zf.read(".clickeye/linear-issues.json"))
    assert content["session_id"] == "session-uuid-123"
    assert content["scenario"] == "versionup"
    assert content["repo_full_name"] == "acme/api"
    assert len(content["issues"]) == 1
    assert content["issues"][0]["linear_identifier"] == "CE-101"


def test_zip_task_file_uses_prompt_md() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        body = zf.read(".ralph/tasks/CE-101.md").decode("utf-8")
    assert "Upgrade Python" in body


def test_zip_task_file_fallback_when_prompt_md_missing() -> None:
    kwargs = {
        **_BASE_KWARGS,
        "recommendations": [
            {
                "id": "rec-2",
                "linear_identifier": "CE-102",
                "title": "fallback prompt",
                "rationale_md": "test rationale",
                "target_path": "pyproject.toml",
                "risk": "low",
                "effort": "S",
                "category": "upgrade",
                # prompt_md 누락
            }
        ],
        "linear_issues": [],
    }
    data = generate_modernize_zip(**kwargs)
    with _open(data) as zf:
        body = zf.read(".ralph/tasks/CE-102.md").decode("utf-8")
    # 폴백 템플릿이 title + Acceptance criteria 를 포함
    assert "fallback prompt" in body
    assert "Acceptance criteria" in body


def test_zip_readme_contains_repo_and_scenario() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        readme = zf.read("MODERNIZE_README.md").decode("utf-8")
    assert "acme/api" in readme
    assert "versionup" in readme
    assert "CE-101" in readme  # 권장안 목록


def test_zip_env_example_has_team_id_placeholder() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        env = zf.read(".env.example").decode("utf-8")
    assert "LINEAR_API_KEY=" in env
    assert "LINEAR_TEAM_ID=team-uuid" in env
    assert "REPO_URL=https://github.com/acme/api" in env


def test_zip_safe_identifier_filename() -> None:
    """linear_identifier 에 특수문자가 있어도 안전한 파일명으로 저장."""
    kwargs = {
        **_BASE_KWARGS,
        "recommendations": [
            {
                "id": "rec-x",
                "linear_identifier": "CE/101?danger",
                "title": "x",
                "prompt_md": "y",
            }
        ],
        "linear_issues": [],
    }
    data = generate_modernize_zip(**kwargs)
    with _open(data) as zf:
        names = zf.namelist()
    # `/` 와 `?` 가 `_` 로 치환됨
    assert any(n == ".ralph/tasks/CE_101_danger.md" for n in names)


def test_zip_empty_recommendations() -> None:
    kwargs = {**_BASE_KWARGS, "recommendations": [], "linear_issues": []}
    data = generate_modernize_zip(**kwargs)
    with _open(data) as zf:
        names = set(zf.namelist())
    # 기본 파일은 다 있어야 함
    assert ".clickeye/linear-issues.json" in names
    assert "MODERNIZE_README.md" in names
    # 권장안이 없으면 .ralph/tasks 하위 파일 X
    assert not any(n.startswith(".ralph/tasks/") for n in names)


def test_zip_deterministic_for_same_input() -> None:
    """동일 입력 → 동일 파일명 set (R-2 핵심)."""
    a = generate_modernize_zip(**_BASE_KWARGS)
    b = generate_modernize_zip(**_BASE_KWARGS)
    with _open(a) as za, _open(b) as zb:
        assert set(za.namelist()) == set(zb.namelist())
