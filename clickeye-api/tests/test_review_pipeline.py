"""교차 리뷰 파이프라인 API 테스트."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import encrypt
from app.models.user_linear_credentials import UserLinearCredentials


@pytest.fixture
async def project_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    """테스트용 프로젝트 생성 후 ID 반환."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "리뷰 파이프라인 테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def session_id(client: AsyncClient, auth_headers: dict[str, str], project_id: str) -> str:
    """오케스트레이션 세션 생성 → 분해 → 배정 → drafting 전이까지."""
    # 세션 생성
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={
            "title": "교차 리뷰 테스트",
            "description": "메인+서브 AI 교차 리뷰 파이프라인 테스트",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # 분해 → 배정 → drafting 전이
    await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/decompose",
        json={},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/assign",
        json={},
        headers=auth_headers,
    )
    await client.put(
        f"/api/v1/orchestrator/sessions/{sid}/transition",
        json={"target_phase": "drafting"},
        headers=auth_headers,
    )
    return sid


@pytest.fixture
async def round_id(client: AsyncClient, auth_headers: dict[str, str], session_id: str) -> str:
    """리뷰 라운드 생성 후 ID 반환."""
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "def hello():\n    return 'Hello, World!'",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# === 초안 제출 테스트 ===


@pytest.mark.asyncio
async def test_submit_draft(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """메인 AI 초안 제출 → 리뷰 라운드 생성."""
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "class UserService:\n    pass",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft_submitted"
    assert body["main_ai_role"] == "backend"
    assert body["round_number"] == 1
    assert body["review_content"] is None


@pytest.mark.asyncio
async def test_submit_draft_wrong_phase(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """requested 단계에서 초안 제출 → 422."""
    # requested 상태의 세션
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "위상 테스트"},
        headers=auth_headers,
    )
    sid = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "초안 내용",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_draft_no_auth(client: AsyncClient, session_id: str) -> None:
    """인증 없이 초안 제출 → 401/403."""
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "초안",
        },
    )
    assert resp.status_code in (401, 403)


# === 교차 리뷰 제출 테스트 ===


@pytest.mark.asyncio
async def test_submit_review(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """서브 AI 교차 리뷰 제출 → review_completed."""
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "함수에 docstring 추가 필요. 에러 핸들링 부족.",
            "review_score": 65,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "review_completed"
    assert body["sub_ai_role"] == "reviewer"
    assert body["review_score"] == 65
    assert body["diff_summary"] is not None


@pytest.mark.asyncio
async def test_submit_counter_argument(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """반론 리뷰 제출."""
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "architect",
            "review_type": "counter_argument",
            "review_content": "이 설계는 확장성 문제가 있음. 인터페이스 분리 권장.",
            "review_score": 50,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["review_type"] == "counter_argument"


@pytest.mark.asyncio
async def test_submit_review_on_merged_round(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """이미 병합된 라운드에 리뷰 → 422."""
    # 리뷰 완료
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "LGTM",
            "review_score": 90,
        },
        headers=auth_headers,
    )
    # 병합
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_draft"},
        headers=auth_headers,
    )
    # 다시 리뷰 시도
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "추가 리뷰",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === diff 조회 테스트 ===


@pytest.mark.asyncio
async def test_get_diff(client: AsyncClient, auth_headers: dict[str, str], round_id: str) -> None:
    """리뷰 후 diff 조회."""
    # 리뷰 제출
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "def hello():\n    '''인사 함수.'''\n    return 'Hello!'",
        },
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/orchestrator/reviews/{round_id}/diff",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["diff_summary"] is not None
    assert body["draft_content"] != ""
    assert body["review_content"] != ""


@pytest.mark.asyncio
async def test_get_diff_no_review(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """리뷰 미제출 상태에서 diff 조회 → 422."""
    resp = await client.get(
        f"/api/v1/orchestrator/reviews/{round_id}/diff",
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === 병합 테스트 ===


@pytest.mark.asyncio
async def test_merge_accept_draft(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """초안 채택 병합."""
    # 리뷰 제출
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "사소한 수정만 필요",
            "review_score": 85,
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_draft"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "merged"
    assert body["merge_strategy"] == "accept_draft"
    assert body["merged_content"] == body["draft_content"]


@pytest.mark.asyncio
async def test_merge_accept_review(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """리뷰 채택 병합."""
    review_content = "def hello():\n    '''인사 함수.'''\n    return 'Hello, World!'"
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "alternative",
            "review_content": review_content,
            "review_score": 95,
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_review"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["merged_content"] == review_content


@pytest.mark.asyncio
async def test_merge_manual(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """수동 병합."""
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "개선된 구현",
        },
        headers=auth_headers,
    )

    merged = "def hello():\n    '''최종 병합 결과.'''\n    return 'Merged!'"
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={
            "merge_strategy": "manual_merge",
            "merged_content": merged,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["merged_content"] == merged


@pytest.mark.asyncio
async def test_merge_manual_without_content(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """manual_merge에서 merged_content 미제공 → 422."""
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "리뷰",
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "manual_merge"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_merge_before_review(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """리뷰 전 병합 시도 → 422."""
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_draft"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === 거절 테스트 ===


@pytest.mark.asyncio
async def test_reject_review(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """리뷰 거절 → rejected 상태."""
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "품질 미달",
            "review_score": 30,
        },
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/reject",
        json={"reason": "리뷰 품질 미달 — 재작성 필요"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_reject_before_review(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """리뷰 전 거절 → 422."""
    resp = await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/reject",
        json={"reason": "조기 거절"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === 라운드 조회 테스트 ===


@pytest.mark.asyncio
async def test_list_review_rounds(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """라운드 목록 조회."""
    # 2개 라운드 생성
    for i in range(2):
        await client.post(
            f"/api/v1/orchestrator/sessions/{session_id}/reviews",
            json={
                "main_ai_role": "backend",
                "draft_content": f"초안 {i}",
            },
            headers=auth_headers,
        )

    resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][0]["round_number"] == 1
    assert body["items"][1]["round_number"] == 2


@pytest.mark.asyncio
async def test_get_review_round(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """라운드 상세 조회."""
    resp = await client.get(
        f"/api/v1/orchestrator/reviews/{round_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == round_id


@pytest.mark.asyncio
async def test_get_review_round_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 라운드 → 404."""
    resp = await client.get(
        "/api/v1/orchestrator/reviews/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# === 이벤트 이력 테스트 ===


@pytest.mark.asyncio
async def test_review_events(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """이벤트 이력 조회 — 초안 제출 이벤트."""
    resp = await client.get(
        f"/api/v1/orchestrator/reviews/{round_id}/events",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "draft_submitted"


@pytest.mark.asyncio
async def test_review_events_full_cycle(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """전체 사이클 이벤트 — 초안→리뷰→병합."""
    # 리뷰 제출
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/review",
        json={
            "sub_ai_role": "reviewer",
            "review_type": "cross_review",
            "review_content": "LGTM",
            "review_score": 90,
        },
        headers=auth_headers,
    )
    # 병합
    await client.post(
        f"/api/v1/orchestrator/reviews/{round_id}/merge",
        json={"merge_strategy": "accept_draft"},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/orchestrator/reviews/{round_id}/events",
        headers=auth_headers,
    )
    events = resp.json()
    event_types = [e["event_type"] for e in events]
    assert "draft_submitted" in event_types
    assert "review_submitted" in event_types
    assert "merged" in event_types


# === 프롬프트 생성 테스트 ===


@pytest.mark.asyncio
async def test_get_review_prompt(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """교차 리뷰 프롬프트 생성."""
    resp = await client.get(
        f"/api/v1/orchestrator/reviews/{round_id}/prompt",
        params={"review_type": "cross_review"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["main_ai_role"] == "backend"
    assert "정확성 검증" in body["instructions"]
    assert body["draft_content"] != ""


@pytest.mark.asyncio
async def test_get_counter_argument_prompt(
    client: AsyncClient, auth_headers: dict[str, str], round_id: str
) -> None:
    """반론 프롬프트 생성."""
    resp = await client.get(
        f"/api/v1/orchestrator/reviews/{round_id}/prompt",
        params={"review_type": "counter_argument"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "잠재적 문제점" in resp.json()["instructions"]


# === 전체 파이프라인 흐름 테스트 ===


@pytest.mark.asyncio
async def test_full_review_pipeline(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """04(초안)→05(교차리뷰)→06(수정통합) 전체 파이프라인."""
    # 1. 메인 AI 초안 제출 (04단계)
    draft_resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "class AuthService:\n    def login(self): pass",
        },
        headers=auth_headers,
    )
    assert draft_resp.status_code == 201
    rid = draft_resp.json()["id"]

    # 2. 프롬프트 조회
    prompt_resp = await client.get(
        f"/api/v1/orchestrator/reviews/{rid}/prompt",
        headers=auth_headers,
    )
    assert prompt_resp.status_code == 200

    # 3. 서브 AI 교차 리뷰 (05단계)
    review_resp = await client.post(
        f"/api/v1/orchestrator/reviews/{rid}/review",
        json={
            "sub_ai_role": "security",
            "review_type": "cross_review",
            "review_content": (
                "class AuthService:\n"
                "    def login(self, credentials: Credentials) -> Token:\n"
                "        '''인증 후 JWT 토큰 반환.'''\n"
                "        validated = self._validate(credentials)\n"
                "        return self._generate_token(validated)"
            ),
            "review_score": 75,
        },
        headers=auth_headers,
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["status"] == "review_completed"

    # 4. diff 확인
    diff_resp = await client.get(
        f"/api/v1/orchestrator/reviews/{rid}/diff",
        headers=auth_headers,
    )
    assert diff_resp.status_code == 200
    assert diff_resp.json()["diff_summary"] != ""

    # 5. 수정 통합 (06단계)
    merge_resp = await client.post(
        f"/api/v1/orchestrator/reviews/{rid}/merge",
        json={
            "merge_strategy": "accept_review",
            "message": "보안팀 리뷰 결과 반영",
        },
        headers=auth_headers,
    )
    assert merge_resp.status_code == 200
    assert merge_resp.json()["status"] == "merged"

    # 6. 이벤트 이력 확인 (3개: 초안, 리뷰, 병합)
    events_resp = await client.get(
        f"/api/v1/orchestrator/reviews/{rid}/events",
        headers=auth_headers,
    )
    assert len(events_resp.json()) == 3


@pytest.mark.asyncio
async def test_review_rejection_cycle(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """거절 후 재작성 사이클 — 라운드 1 거절 → 라운드 2 생성."""
    # 라운드 1: 초안 제출
    r1 = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "initial draft",
        },
        headers=auth_headers,
    )
    rid1 = r1.json()["id"]

    # 리뷰 제출
    await client.post(
        f"/api/v1/orchestrator/reviews/{rid1}/review",
        json={
            "sub_ai_role": "qa",
            "review_type": "cross_review",
            "review_content": "품질 미달",
            "review_score": 20,
        },
        headers=auth_headers,
    )

    # 거절
    reject_resp = await client.post(
        f"/api/v1/orchestrator/reviews/{rid1}/reject",
        json={"reason": "재작성 필요"},
        headers=auth_headers,
    )
    assert reject_resp.json()["status"] == "rejected"

    # 라운드 2: 개선된 초안
    r2 = await client.post(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        json={
            "main_ai_role": "backend",
            "draft_content": "improved draft with better quality",
        },
        headers=auth_headers,
    )
    assert r2.status_code == 201
    assert r2.json()["round_number"] == 2

    # 라운드 목록 확인
    list_resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}/reviews",
        headers=auth_headers,
    )
    assert list_resp.json()["total"] == 2


# === push-to-linear 테스트 ===


@pytest.fixture
async def session_with_description(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> str:
    """description이 있는 오케스트레이션 세션 생성 → 분해 → 배정."""
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={
            "title": "React + FastAPI 프로젝트 첫 세팅",
            "description": "React 프론트엔드와 FastAPI 백엔드로 구성된 "
            "풀스택 프로젝트의 초기 세팅을 구현해주세요.",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/decompose", json={}, headers=auth_headers
    )
    await client.post(f"/api/v1/orchestrator/sessions/{sid}/assign", json={}, headers=auth_headers)
    return sid


async def _seed_linear_credentials(db_session: AsyncSession, user_id: str) -> None:
    """테스트용 Linear 자격증명을 DB에 시딩한다."""
    import uuid

    creds = UserLinearCredentials(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        encrypted_api_key=encrypt("fake-linear-api-key"),
        team_id="test-team-id",
    )
    db_session.add(creds)
    await db_session.commit()


@pytest.mark.asyncio
async def test_push_to_linear_includes_session_description(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    session_with_description: str,
) -> None:
    """push-to-linear 시 session.description이 create_issues에 전달되는지."""
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    await _seed_linear_credentials(db_session, me.json()["id"])

    captured: dict = {}

    def fake_create_issues(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return [
            {
                "identifier": "TEST-1",
                "title": "[backend] 세팅",
                "url": "https://linear.app/test/TEST-1",
            }
        ]

    with (
        patch("app.services.linear_service.create_issues", side_effect=fake_create_issues),
        patch("app.services.linear_service.get_queued_state_id", return_value=None),
    ):
        resp = await client.post(
            f"/api/v1/orchestrator/sessions/{session_with_description}/push-to-linear",
            headers=auth_headers,
        )

    assert resp.status_code == 201
    assert resp.json()["count"] >= 1
    assert captured.get("session_description") == (
        "React 프론트엔드와 FastAPI 백엔드로 구성된 풀스택 프로젝트의 초기 세팅을 구현해주세요."
    )


@pytest.mark.asyncio
async def test_push_to_linear_without_description(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    project_id: str,
) -> None:
    """session.description=None 일 때 session_description=None으로 전달되고 200 반환."""
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "설명 없는 세션"},
        headers=auth_headers,
    )
    sid = resp.json()["id"]
    await client.post(
        f"/api/v1/orchestrator/sessions/{sid}/decompose", json={}, headers=auth_headers
    )
    await client.post(f"/api/v1/orchestrator/sessions/{sid}/assign", json={}, headers=auth_headers)

    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    await _seed_linear_credentials(db_session, me.json()["id"])

    captured: dict = {}

    def fake_create_issues(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured.update(kwargs)
        return [
            {
                "identifier": "TEST-2",
                "title": "[backend] 태스크",
                "url": "https://linear.app/test/TEST-2",
            }
        ]

    with (
        patch("app.services.linear_service.create_issues", side_effect=fake_create_issues),
        patch("app.services.linear_service.get_queued_state_id", return_value=None),
    ):
        resp = await client.post(
            f"/api/v1/orchestrator/sessions/{sid}/push-to-linear",
            headers=auth_headers,
        )

    assert resp.status_code == 201
    assert captured.get("session_description") is None


@pytest.mark.asyncio
async def test_push_to_linear_no_credentials(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_with_description: str,
) -> None:
    """Linear 자격증명 미설정 시 422 반환."""
    resp = await client.post(
        f"/api/v1/orchestrator/sessions/{session_with_description}/push-to-linear",
        headers=auth_headers,
    )
    assert resp.status_code == 422
