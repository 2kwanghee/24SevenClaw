"""linear_service.create_issues 단위 테스트 — description 포맷 검증."""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.review_pipeline import LinearSyncHintSubtask
from app.services.linear_service import create_issues


def _make_subtask(title: str = "서브태스크 제목", role: str = "backend", summary: str = "초안 내용") -> LinearSyncHintSubtask:
    return LinearSyncHintSubtask(title=title, role=role, draft_summary=summary)


def _call_create_issues(subtasks: list[LinearSyncHintSubtask], session_description: str | None) -> list[dict]:
    """_call을 mock하고 create_issues를 호출. 전달된 GraphQL 변수를 반환."""
    captured_vars: list[dict] = []

    def fake_call(api_key: str, query: str, variables: dict) -> dict:
        captured_vars.append(variables)
        return {"issueCreate": {"issue": {"identifier": "T-1", "title": "...", "url": "..."}}}

    with patch("app.services.linear_service._call", side_effect=fake_call):
        create_issues(
            api_key="fake-key",
            team_id="team-1",
            subtasks=subtasks,
            session_description=session_description,
        )
    return captured_vars


@pytest.mark.asyncio
async def test_description_includes_session_context() -> None:
    """session_description이 있으면 이슈 description에 ## 원본 요구사항 블록이 prepend된다."""
    session_desc = "React + FastAPI 프로젝트 첫 세팅"
    subtask = _make_subtask(summary="백엔드 초기 설정")

    vars_list = _call_create_issues([subtask], session_description=session_desc)

    description = vars_list[0]["input"]["description"]
    assert description.startswith("## 원본 요구사항")
    assert session_desc in description
    assert "백엔드 초기 설정" in description
    assert "---" in description


@pytest.mark.asyncio
async def test_description_no_session_context() -> None:
    """session_description이 None이면 draft_summary만 그대로 사용된다."""
    subtask = _make_subtask(summary="백엔드 초기 설정")

    vars_list = _call_create_issues([subtask], session_description=None)

    description = vars_list[0]["input"]["description"]
    assert description == "백엔드 초기 설정"
    assert "원본 요구사항" not in description


@pytest.mark.asyncio
async def test_description_whitespace_only_session_context() -> None:
    """session_description이 whitespace만 있으면 prepend 블록 없이 draft_summary만 사용한다."""
    subtask = _make_subtask(summary="초안 내용")

    vars_list = _call_create_issues([subtask], session_description="   \n\t  ")

    description = vars_list[0]["input"]["description"]
    assert description == "초안 내용"
    assert "원본 요구사항" not in description


@pytest.mark.asyncio
async def test_multiple_subtasks_all_include_context() -> None:
    """여러 서브태스크 모두 동일한 원본 요구사항 블록을 가진다."""
    session_desc = "풀스택 세팅"
    subtasks = [
        _make_subtask(title="프론트", role="frontend", summary="React 세팅"),
        _make_subtask(title="백엔드", role="backend", summary="FastAPI 세팅"),
    ]

    vars_list = _call_create_issues(subtasks, session_description=session_desc)

    assert len(vars_list) == 2
    for v in vars_list:
        desc = v["input"]["description"]
        assert "## 원본 요구사항" in desc
        assert session_desc in desc


@pytest.mark.asyncio
async def test_issue_title_format() -> None:
    """이슈 title은 [role] title 포맷이다."""
    subtask = _make_subtask(title="API 설계", role="architect")

    vars_list = _call_create_issues([subtask], session_description=None)

    assert vars_list[0]["input"]["title"] == "[architect] API 설계"
