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


def _call(api_key: str, query: str, variables: dict | None = None) -> dict:  # type: ignore[type-arg]
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = Request(LINEAR_API, data=body, method="POST")
    req.add_header("Authorization", api_key)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
    except HTTPError as exc:
        raise RuntimeError(f"Linear API 오류 {exc.code}: {exc.read().decode()[:200]}") from exc
    if "errors" in data:
        msgs = [e.get("message", "") for e in data["errors"]]
        raise RuntimeError(f"Linear GraphQL 오류: {'; '.join(msgs)}")
    return data.get("data", {})


def create_issues(
    api_key: str,
    team_id: str,
    subtasks: list[LinearSyncHintSubtask],
    labels: list[str] | None = None,
) -> list[dict]:  # type: ignore[type-arg]
    """subtasks 목록을 Linear 이슈로 생성. 생성된 이슈 정보 반환."""
    created = []
    for st in subtasks:
        title = f"[{st.role}] {st.title}"
        description = st.draft_summary
        variables = {
            "input": {
                "teamId": team_id,
                "title": title,
                "description": description,
            }
        }
        if labels:
            variables["input"]["labelNames"] = labels

        data = _call(api_key, _ISSUE_CREATE, variables)
        issue = data.get("issueCreate", {}).get("issue") or {}
        created.append(
            {
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
