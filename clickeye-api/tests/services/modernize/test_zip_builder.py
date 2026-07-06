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
    assert "plan.json" in names
    assert "scripts/modernize_pipeline.sh" in names
    assert "scripts/orchestrator.py" in names


def test_zip_plan_json_contains_task_matching_recommendation() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        plan = json.loads(zf.read("plan.json"))
    assert plan["session_id"] == "session-uuid-123"
    assert plan["repo_full_name"] == "acme/api"
    task_ids = {t["id"] for t in plan["tasks"]}
    assert "CE-101" in task_ids
    task = next(t for t in plan["tasks"] if t["id"] == "CE-101")
    assert task["prompt_file"] == ".ralph/tasks/CE-101.md"
    assert task["risk"] == "high"


def test_zip_orchestrator_script_is_valid_python() -> None:
    data = generate_modernize_zip(**_BASE_KWARGS)
    with _open(data) as zf:
        source = zf.read("scripts/orchestrator.py").decode("utf-8")
    compile(source, "orchestrator.py", "exec")


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
