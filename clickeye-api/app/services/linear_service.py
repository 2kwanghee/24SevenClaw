"""Linear GraphQL API 서비스 — 사용자 자격증명으로 대행 호출."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from app.schemas.review_pipeline import LinearSyncHintSubtask

LINEAR_API = "https://api.linear.app/graphql"

_ISSUE_CREATE = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier title url }
  }
}
"""

_WEBHOOK_CREATE = """
mutation WebhookCreate($input: WebhookCreateInput!) {
  webhookCreate(input: $input) {
    success
    webhook { id url }
  }
}
"""

_WEBHOOK_UPDATE = """
mutation WebhookUpdate($id: String!, $input: WebhookUpdateInput!) {
  webhookUpdate(id: $id, input: $input) {
    success
    webhook { id url }
  }
}
"""

_WEBHOOKS_QUERY = """
query Webhooks {
  webhooks { nodes { id url label } }
}
"""

_VIEWER_QUERY = """
query Viewer {
  viewer { id name email }
}
"""

_TEAM_QUERY = """
query Team($id: String!) {
  team(id: $id) { id name }
}
"""

_TEAM_STATES_QUERY = """
query TeamStates($id: String!) {
  team(id: $id) {
    states { nodes { id name type position } }
  }
}
"""

_ISSUE_UPDATE = """
mutation IssueUpdate($id: String!, $stateId: String!) {
  issueUpdate(id: $id, input: { stateId: $stateId }) {
    success
  }
}
"""


def _call(api_key: str, query: str, variables: dict | None = None, timeout: int = 15) -> dict:  # type: ignore[type-arg]
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = Request(LINEAR_API, data=body, method="POST")
    req.add_header("Authorization", api_key)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except HTTPError as exc:
        raise RuntimeError(f"Linear API 오류 {exc.code}: {exc.read().decode()[:200]}") from exc
    if "errors" in data:
        msgs = [e.get("message", "") for e in data["errors"]]
        raise RuntimeError(f"Linear GraphQL 오류: {'; '.join(msgs)}")
    result: dict[str, object] = data.get("data", {})
    return result


def get_initial_state_id(api_key: str, team_id: str) -> str | None:
    """이슈 최초 등록 시 부여할 상태 ID를 반환한다.

    우선순위: Wait (검수 대기) — 사람이 승인 후 Queued로 전이한다.
    Wait 상태가 없으면 None을 반환해 Linear 기본 상태로 생성한다.
    """
    try:
        data = _call(api_key, _TEAM_STATES_QUERY, {"id": team_id})
        nodes = data.get("team", {}).get("states", {}).get("nodes", [])
        priority = ["wait"]
        by_name = {str(s.get("name", "")).lower(): str(s["id"]) for s in nodes}
        for name in priority:
            if name in by_name:
                return by_name[name]
    except RuntimeError:
        pass
    return None


def get_queued_state_id(api_key: str, team_id: str) -> str | None:
    """Queued 상태 ID를 반환한다. 사람 승인 시 Wait → Queued 전이에 사용."""
    try:
        data = _call(api_key, _TEAM_STATES_QUERY, {"id": team_id})
        nodes = data.get("team", {}).get("states", {}).get("nodes", [])
        priority = ["dayqueued", "nightqueued", "queued"]
        by_name = {str(s.get("name", "")).lower(): str(s["id"]) for s in nodes}
        for name in priority:
            if name in by_name:
                return by_name[name]
    except RuntimeError:
        pass
    return None


def update_issue_state_id(api_key: str, issue_id: str, state_id: str) -> bool:
    """이미 알고 있는 stateId로 Linear 이슈 상태를 직접 변경한다."""
    try:
        result = _call(api_key, _ISSUE_UPDATE, {"id": issue_id, "stateId": state_id})
        return bool(result.get("issueUpdate", {}).get("success"))
    except RuntimeError:
        return False





def validate_credentials(api_key: str, team_id: str) -> tuple[bool, str]:
    """Linear API 키와 팀 ID 유효성 검증. 실제 API 호출로 인증 확인."""
    try:
        _call(api_key, _VIEWER_QUERY)
    except RuntimeError as exc:
        return False, f"API 키 인증 실패: {exc}"
    try:
        data = _call(api_key, _TEAM_QUERY, {"id": team_id})
        team = data.get("team")
        if not team:
            return False, "팀 ID를 찾을 수 없습니다. UUID 형식인지 확인하세요."
        return True, f"인증 성공 ({team.get('name', team_id)})"
    except RuntimeError as exc:
        return False, f"팀 ID 조회 실패: {exc}"


def create_initial_task(api_key: str, team_id: str, project_name: str) -> str | None:
    """프로젝트 생성 완료 알림 이슈를 생성하고 URL을 반환한다."""
    variables = {
        "input": {
            "teamId": team_id,
            "title": f"[{project_name}] 프로젝트 생성 완료",
            "description": (
                f"ClickEye 위저드에서 **{project_name}** 프로젝트가 성공적으로 생성되었습니다.\n\n"
                "ZIP 파일을 다운로드하고 README의 안내에 따라 로컬 환경을 설정하세요."
            ),
        }
    }
    data = _call(api_key, _ISSUE_CREATE, variables)
    issue = data.get("issueCreate", {}).get("issue") or {}
    return issue.get("url") or None


def create_issues(
    api_key: str,
    team_id: str,
    subtasks: list[LinearSyncHintSubtask],
    label_ids: list[str] | None = None,
    state_id: str | None = None,
    *,
    session_description: str | None = None,
) -> list[dict]:  # type: ignore[type-arg]
    """subtasks 목록을 Linear 이슈로 생성. 생성된 이슈 정보 반환."""
    base = (session_description or "").strip()
    created = []
    for st in subtasks:
        title = f"[{st.role}] {st.title}"
        if base:
            description = f"## 원본 요구사항\n\n{base}\n\n---\n\n{st.draft_summary}"
        else:
            description = st.draft_summary
        variables: dict = {  # type: ignore[type-arg]
            "input": {
                "teamId": team_id,
                "title": title,
                "description": description,
            }
        }
        if label_ids:
            variables["input"]["labelIds"] = label_ids
        if state_id:
            variables["input"]["stateId"] = state_id

        data = _call(api_key, _ISSUE_CREATE, variables)
        issue = data.get("issueCreate", {}).get("issue") or {}
        created.append(
            {
                "id": issue.get("id", ""),
                "identifier": issue.get("identifier", ""),
                "title": issue.get("title", ""),
                "url": issue.get("url", ""),
            }
        )
    return created


def ensure_webhook(
    api_key: str,
    team_id: str,
    url: str,
    secret: str | None = None,
    label: str = "24SevenClaw",
) -> str:
    """Linear 워크스페이스에 webhook을 등록하거나 기존 URL을 갱신한다.

    Returns:
        생성/갱신된 webhook ID
    """
    data = _call(api_key, _WEBHOOKS_QUERY)
    existing = data.get("webhooks", {}).get("nodes", [])

    for wh in existing:
        if wh.get("label") == label:
            _call(
                api_key,
                _WEBHOOK_UPDATE,
                {"id": wh["id"], "input": {"url": url, "secret": secret}},
            )
            return str(wh["id"])

    variables: dict = {  # type: ignore[type-arg]
        "input": {
            "teamId": team_id,
            "url": url,
            "label": label,
            "resourceTypes": ["Issue"],
            "allPublicTeams": False,
        }
    }
    if secret:
        variables["input"]["secret"] = secret

    result = _call(api_key, _WEBHOOK_CREATE, variables)
    webhook = result.get("webhookCreate", {}).get("webhook") or {}
    return str(webhook.get("id", ""))
