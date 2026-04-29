"""finalize_session 초기 태스크 자동 등록 테스트."""
from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _setup_finalize_prerequisites(
    client: AsyncClient,
    headers: dict[str, str],
    pm_ids: list[str],
) -> tuple[str, str, str]:
    """조직/세션/프로토타입 생성 후 프로토타입·PM 선택. session_id, prototype_id, pm_id 반환."""
    # 조직 생성
    org_resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "테스트 회사", "size": "11-50", "industry": "IT"},
        headers=headers,
    )
    org_id = org_resp.json()["id"]

    # 세션 생성
    sess_resp = await client.post(
        "/api/v1/prototype-sessions/",
        json={
            "organization_id": org_id,
            "solution_prompt": "SaaS 구독 관리 서비스를 만들고 싶습니다",
        },
        headers=headers,
    )
    assert sess_resp.status_code == 201
    session_id = sess_resp.json()["id"]

    # 프로토타입 생성 (백그라운드 동기 실행)
    await client.post(
        f"/api/v1/prototype-sessions/{session_id}/prototypes/generate",
        headers=headers,
    )

    # 프로토타입 목록 조회
    proto_resp = await client.get(
        f"/api/v1/prototype-sessions/{session_id}/prototypes",
        headers=headers,
    )
    assert proto_resp.status_code == 200
    prototype_id = proto_resp.json()["items"][0]["id"]

    # 프로토타입 + PM 선택
    await client.patch(
        f"/api/v1/prototype-sessions/{session_id}",
        json={"selected_prototype_id": prototype_id, "selected_pm_id": pm_ids[0]},
        headers=headers,
    )

    return session_id, prototype_id, pm_ids[0]


@pytest.mark.asyncio
async def test_finalize_without_integrations(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_pm_profiles: list[str],
) -> None:
    """통합 자격증명 없이 finalize 호출 시 프로젝트 생성 성공, initial_task_url=None."""
    session_id, _, _ = await _setup_finalize_prerequisites(
        client, auth_headers, seeded_pm_profiles
    )

    resp = await client.post(
        f"/api/v1/prototype-sessions/{session_id}/finalize",
        json={"project_name": "테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["project_name"] == "테스트 프로젝트"
    assert body["initial_task_url"] is None


@pytest.mark.asyncio
async def test_finalize_with_linear_creates_initial_task(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_pm_profiles: list[str],
) -> None:
    """Linear 자격증명 포함 finalize 시 초기 이슈가 생성되고 URL이 저장된다."""
    session_id, _, _ = await _setup_finalize_prerequisites(
        client, auth_headers, seeded_pm_profiles
    )

    with patch(
        "app.services.linear_service.create_initial_task",
        return_value="https://linear.app/test/issue/TEST-1",
    ):
        resp = await client.post(
            f"/api/v1/prototype-sessions/{session_id}/finalize",
            json={
                "project_name": "Linear 연동 프로젝트",
                "linear_api_key": "lin_api_testkey",
                "linear_team_id": "team-uuid-1234",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["initial_task_url"] == "https://linear.app/test/issue/TEST-1"


@pytest.mark.asyncio
async def test_finalize_with_notion_creates_initial_task(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_pm_profiles: list[str],
) -> None:
    """Notion 자격증명 포함 finalize 시 초기 페이지가 생성되고 URL이 저장된다."""
    session_id, _, _ = await _setup_finalize_prerequisites(
        client, auth_headers, seeded_pm_profiles
    )

    with patch(
        "app.services.notion_service.create_initial_task",
        return_value="https://notion.so/test-page-id",
    ):
        resp = await client.post(
            f"/api/v1/prototype-sessions/{session_id}/finalize",
            json={
                "project_name": "Notion 연동 프로젝트",
                "notion_api_key": "secret_testkey",
                "notion_database_id": "db-uuid-5678",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["initial_task_url"] == "https://notion.so/test-page-id"


@pytest.mark.asyncio
async def test_finalize_integration_failure_does_not_fail_project(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_pm_profiles: list[str],
) -> None:
    """Linear 태스크 생성 실패 시에도 프로젝트 생성은 성공한다."""
    session_id, _, _ = await _setup_finalize_prerequisites(
        client, auth_headers, seeded_pm_profiles
    )

    with patch(
        "app.services.linear_service.create_initial_task",
        side_effect=RuntimeError("Linear API 오류"),
    ):
        resp = await client.post(
            f"/api/v1/prototype-sessions/{session_id}/finalize",
            json={
                "project_name": "실패 허용 프로젝트",
                "linear_api_key": "lin_api_badkey",
                "linear_team_id": "bad-team-id",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["project_name"] == "실패 허용 프로젝트"
    assert body["initial_task_url"] is None


@pytest.mark.asyncio
async def test_finalize_linear_preferred_over_notion(
    client: AsyncClient,
    auth_headers: dict[str, str],
    seeded_pm_profiles: list[str],
) -> None:
    """Linear와 Notion 모두 제공 시 Linear URL이 우선 저장된다."""
    session_id, _, _ = await _setup_finalize_prerequisites(
        client, auth_headers, seeded_pm_profiles
    )

    with (
        patch(
            "app.services.linear_service.create_initial_task",
            return_value="https://linear.app/test/issue/TEST-2",
        ),
        patch(
            "app.services.notion_service.create_initial_task",
            return_value="https://notion.so/test-page-id-2",
        ),
    ):
        resp = await client.post(
            f"/api/v1/prototype-sessions/{session_id}/finalize",
            json={
                "project_name": "양쪽 연동 프로젝트",
                "linear_api_key": "lin_api_testkey",
                "linear_team_id": "team-uuid-1234",
                "notion_api_key": "secret_testkey",
                "notion_database_id": "db-uuid-5678",
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["initial_task_url"] == "https://linear.app/test/issue/TEST-2"
