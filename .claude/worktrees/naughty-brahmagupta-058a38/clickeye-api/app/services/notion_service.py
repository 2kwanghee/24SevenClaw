"""Notion API 서비스 — 유효성 검증 및 페이지 생성."""
from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _call(
    api_key: str,
    method: str,
    path: str,
    body: dict | None = None,  # type: ignore[type-arg]
    timeout: int = 15,
) -> dict:  # type: ignore[type-arg]
    url = f"{NOTION_API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())  # type: ignore[no-any-return]
    except HTTPError as exc:
        raise RuntimeError(
            f"Notion API 오류 {exc.code}: {exc.read().decode()[:200]}"
        ) from exc


def validate_credentials(api_key: str, database_id: str) -> tuple[bool, str]:
    """Notion API 키와 데이터베이스 ID 유효성 검증. 실제 API 호출로 인증 확인."""
    try:
        _call(api_key, "GET", "/users/me")
    except RuntimeError as exc:
        return False, f"API 키 인증 실패: {exc}"
    try:
        result = _call(api_key, "GET", f"/databases/{database_id}")
        title_arr = result.get("title", [])
        db_title = (
            title_arr[0].get("plain_text", database_id) if title_arr else database_id
        )
        return True, f"인증 성공 ({db_title})"
    except RuntimeError as exc:
        return False, f"데이터베이스 ID 조회 실패: {exc}"


def create_page(
    api_key: str,
    database_id: str,
    title: str,
    body: str,
) -> str | None:
    """Notion 데이터베이스에 새 페이지를 생성하고 URL을 반환한다."""
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": body}}]
                },
            }
        ],
    }
    result = _call(api_key, "POST", "/pages", payload)
    return result.get("url") or None


def create_initial_task(
    api_key: str, database_id: str, project_name: str
) -> str | None:
    """프로젝트 생성 완료 알림 페이지를 Notion에 생성하고 URL을 반환한다."""
    title = f"[{project_name}] 프로젝트 생성 완료"
    body = (
        f"ClickEye 위저드에서 {project_name} 프로젝트가 성공적으로 생성되었습니다.\n\n"
        "ZIP 파일을 다운로드하고 README의 안내에 따라 로컬 환경을 설정하세요."
    )
    return create_page(api_key, database_id, title, body)
