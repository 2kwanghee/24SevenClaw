"""품질 검증 게이트 API 테스트."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def project_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    """테스트용 프로젝트 생성 후 ID 반환."""
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "품질 검증 테스트 프로젝트"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
async def session_id(client: AsyncClient, auth_headers: dict[str, str], project_id: str) -> str:
    """오케스트레이션 세션을 validating 단계까지 전이."""
    # 세션 생성
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={
            "title": "품질 검증 테스트",
            "description": "품질 게이트 자동화 테스트",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    sid = resp.json()["id"]

    # requested → decomposed → assigned → drafting → reviewing → integrating → validating
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
    for target in ["drafting", "reviewing", "integrating", "validating"]:
        await client.put(
            f"/api/v1/orchestrator/sessions/{sid}/transition",
            json={"target_phase": target},
            headers=auth_headers,
        )

    return sid


@pytest.fixture
async def run_id(client: AsyncClient, auth_headers: dict[str, str], session_id: str) -> str:
    """검증 실행 생성 후 ID 반환."""
    resp = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={"threshold": 70},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


# === 검증 실행 생성 테스트 ===


@pytest.mark.asyncio
async def test_create_run(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """validating 단계에서 검증 실행 생성."""
    resp = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={"threshold": 80},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["threshold"] == 80
    assert body["run_number"] == 1
    assert body["checks_total"] == 0


@pytest.mark.asyncio
async def test_create_run_wrong_phase(
    client: AsyncClient, auth_headers: dict[str, str], project_id: str
) -> None:
    """validating이 아닌 단계에서 실행 생성 → 422."""
    # requested 상태의 세션
    resp = await client.post(
        f"/api/v1/orchestrator/projects/{project_id}/sessions",
        json={"title": "위상 테스트"},
        headers=auth_headers,
    )
    sid = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/quality-gate/sessions/{sid}/runs",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_run_no_auth(client: AsyncClient, session_id: str) -> None:
    """인증 없이 실행 생성 → 401/403."""
    resp = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={},
    )
    assert resp.status_code in (401, 403)


# === 검사 결과 제출 테스트 ===


@pytest.mark.asyncio
async def test_submit_check(client: AsyncClient, auth_headers: dict[str, str], run_id: str) -> None:
    """QA 에이전트 검사 결과 제출 → running 상태."""
    resp = await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={
            "category": "code_quality",
            "score": 85,
            "agent_id": "qa-agent-001",
            "details": "복잡도 양호, 명명 규칙 준수",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["category"] == "code_quality"
    assert body["score"] == 85
    assert body["passed"] == "true"
    assert body["agent_id"] == "qa-agent-001"


@pytest.mark.asyncio
async def test_submit_check_failed(
    client: AsyncClient, auth_headers: dict[str, str], run_id: str
) -> None:
    """기준 미달 검사 → passed=false."""
    resp = await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={
            "category": "security",
            "score": 50,
            "details": "SQL 인젝션 취약점 발견",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["passed"] == "false"


@pytest.mark.asyncio
async def test_submit_check_duplicate(
    client: AsyncClient, auth_headers: dict[str, str], run_id: str
) -> None:
    """같은 카테고리 중복 제출 → 409."""
    payload = {"category": "code_quality", "score": 80}
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json=payload,
        headers=auth_headers,
    )
    resp = await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json=payload,
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_submit_check_on_completed_run(
    client: AsyncClient, auth_headers: dict[str, str], run_id: str
) -> None:
    """완료된 실행에 검사 제출 → 422."""
    # 검사 제출 + 평가 완료
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={"category": "code_quality", "score": 90},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )

    # 추가 제출 시도
    resp = await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={"category": "security", "score": 80},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === 평가 테스트 ===


@pytest.mark.asyncio
async def test_evaluate_all_pass(
    client: AsyncClient, auth_headers: dict[str, str], run_id: str
) -> None:
    """모든 검사 통과 → passed + approved."""
    for category, score in [
        ("code_quality", 85),
        ("security", 90),
        ("performance", 75),
    ]:
        await client.post(
            f"/api/v1/quality-gate/runs/{run_id}/checks",
            json={"category": category, "score": score},
            headers=auth_headers,
        )

    resp = await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "passed"
    assert body["verdict"] == "approved"
    assert body["checks_total"] == 3
    assert body["checks_passed"] == 3
    assert body["overall_score"] is not None
    assert body["completed_at"] is not None


@pytest.mark.asyncio
async def test_evaluate_some_fail(
    client: AsyncClient, auth_headers: dict[str, str], run_id: str
) -> None:
    """일부 검사 실패 → failed + rejected."""
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={"category": "code_quality", "score": 85},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={"category": "security", "score": 40},
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["verdict"] == "rejected"
    assert body["checks_passed"] == 1
    assert "security" in body["verdict_reason"]


@pytest.mark.asyncio
async def test_evaluate_no_checks(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """검사 없이 평가 시도 → 422."""
    # pending 상태의 실행은 평가 불가 (running이어야 함)
    resp = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={},
        headers=auth_headers,
    )
    rid = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/quality-gate/runs/{rid}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_evaluate_already_completed(
    client: AsyncClient, auth_headers: dict[str, str], run_id: str
) -> None:
    """이미 완료된 실행 재평가 → 422."""
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={"category": "code_quality", "score": 90},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# === 자동 전이 테스트 ===


@pytest.mark.asyncio
async def test_auto_transition_approved(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """통과 시 세션 자동 전이 → approved."""
    # 실행 생성
    resp = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={"threshold": 70},
        headers=auth_headers,
    )
    rid = resp.json()["id"]

    # 검사 제출 (모두 통과)
    for category in ["code_quality", "security", "performance"]:
        await client.post(
            f"/api/v1/quality-gate/runs/{rid}/checks",
            json={"category": category, "score": 80},
            headers=auth_headers,
        )

    # 평가 (auto_transition=True)
    await client.post(
        f"/api/v1/quality-gate/runs/{rid}/evaluate",
        json={"auto_transition": True},
        headers=auth_headers,
    )

    # 세션 상태 확인
    sess_resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}",
        headers=auth_headers,
    )
    assert sess_resp.json()["phase"] == "approved"


@pytest.mark.asyncio
async def test_auto_transition_rejected(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """실패 시 세션 자동 전이 → integrating (재작업)."""
    resp = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={"threshold": 70},
        headers=auth_headers,
    )
    rid = resp.json()["id"]

    # 검사 제출 (보안 미달)
    await client.post(
        f"/api/v1/quality-gate/runs/{rid}/checks",
        json={"category": "code_quality", "score": 80},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{rid}/checks",
        json={"category": "security", "score": 30},
        headers=auth_headers,
    )

    # 평가 (auto_transition=True)
    await client.post(
        f"/api/v1/quality-gate/runs/{rid}/evaluate",
        json={"auto_transition": True},
        headers=auth_headers,
    )

    # 세션 상태 확인 → integrating (재작업)
    sess_resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}",
        headers=auth_headers,
    )
    assert sess_resp.json()["phase"] == "integrating"


# === 리포트 조회 테스트 ===


@pytest.mark.asyncio
async def test_get_report(client: AsyncClient, auth_headers: dict[str, str], run_id: str) -> None:
    """검증 리포트 조회."""
    # 검사 제출
    for category, score in [("code_quality", 85), ("security", 90)]:
        await client.post(
            f"/api/v1/quality-gate/runs/{run_id}/checks",
            json={"category": category, "score": score},
            headers=auth_headers,
        )

    # 평가
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )

    # 리포트 조회
    resp = await client.get(
        f"/api/v1/quality-gate/runs/{run_id}/report",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["run"]["status"] == "passed"
    assert len(body["checks"]) == 2
    assert body["summary"]["code_quality"] == 85
    assert body["summary"]["security"] == 90


# === 실행 목록 조회 테스트 ===


@pytest.mark.asyncio
async def test_list_runs(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """실행 목록 조회."""
    for _ in range(2):
        await client.post(
            f"/api/v1/quality-gate/sessions/{session_id}/runs",
            json={},
            headers=auth_headers,
        )

    resp = await client.get(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["items"][0]["run_number"] == 1
    assert body["items"][1]["run_number"] == 2


@pytest.mark.asyncio
async def test_get_run(client: AsyncClient, auth_headers: dict[str, str], run_id: str) -> None:
    """실행 상세 조회."""
    resp = await client.get(
        f"/api/v1/quality-gate/runs/{run_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id


@pytest.mark.asyncio
async def test_get_run_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """존재하지 않는 실행 → 404."""
    resp = await client.get(
        "/api/v1/quality-gate/runs/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# === 이벤트 이력 테스트 ===


@pytest.mark.asyncio
async def test_events(client: AsyncClient, auth_headers: dict[str, str], run_id: str) -> None:
    """이벤트 이력 조회 — 생성 이벤트."""
    resp = await client.get(
        f"/api/v1/quality-gate/runs/{run_id}/events",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    events = resp.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "run_created"


@pytest.mark.asyncio
async def test_events_full_cycle(
    client: AsyncClient, auth_headers: dict[str, str], run_id: str
) -> None:
    """전체 사이클 이벤트 — 생성→검사→평가."""
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/checks",
        json={"category": "code_quality", "score": 90},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{run_id}/evaluate",
        json={"auto_transition": False},
        headers=auth_headers,
    )

    resp = await client.get(
        f"/api/v1/quality-gate/runs/{run_id}/events",
        headers=auth_headers,
    )
    events = resp.json()
    event_types = [e["event_type"] for e in events]
    assert "run_created" in event_types
    assert "check_submitted" in event_types
    assert "evaluated" in event_types


# === 전체 파이프라인 흐름 테스트 ===


@pytest.mark.asyncio
async def test_full_quality_gate_pipeline(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """Step 07 전체 흐름: 실행 생성→검사 제출→평가→자동 전이."""
    # 1. 검증 실행 생성
    run_resp = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={"threshold": 60},
        headers=auth_headers,
    )
    assert run_resp.status_code == 201
    rid = run_resp.json()["id"]

    # 2. QA 에이전트가 5개 카테고리 검사 제출
    checks_data = [
        ("code_quality", 85, "qa-code-agent"),
        ("security", 75, "qa-security-agent"),
        ("performance", 70, "qa-perf-agent"),
        ("test_coverage", 80, "qa-test-agent"),
        ("documentation", 65, "qa-doc-agent"),
    ]
    for category, score, agent in checks_data:
        resp = await client.post(
            f"/api/v1/quality-gate/runs/{rid}/checks",
            json={
                "category": category,
                "score": score,
                "agent_id": agent,
                "details": f"{category} 검사 결과",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201

    # 3. 실행 상태 확인 → running
    run_status = await client.get(
        f"/api/v1/quality-gate/runs/{rid}",
        headers=auth_headers,
    )
    assert run_status.json()["status"] == "running"
    assert run_status.json()["checks_total"] == 5

    # 4. 최종 평가 (자동 전이 포함)
    eval_resp = await client.post(
        f"/api/v1/quality-gate/runs/{rid}/evaluate",
        json={"auto_transition": True},
        headers=auth_headers,
    )
    assert eval_resp.status_code == 200
    assert eval_resp.json()["status"] == "passed"
    assert eval_resp.json()["verdict"] == "approved"

    # 5. 세션 상태 확인 → approved
    sess_resp = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}",
        headers=auth_headers,
    )
    assert sess_resp.json()["phase"] == "approved"

    # 6. 리포트 확인
    report_resp = await client.get(
        f"/api/v1/quality-gate/runs/{rid}/report",
        headers=auth_headers,
    )
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert len(report["checks"]) == 5
    assert report["run"]["verdict"] == "approved"

    # 7. 이벤트 이력 확인 (생성 + 5검사 + 평가 + 자동전이)
    events_resp = await client.get(
        f"/api/v1/quality-gate/runs/{rid}/events",
        headers=auth_headers,
    )
    assert len(events_resp.json()) == 8


@pytest.mark.asyncio
async def test_rejection_and_retry_cycle(
    client: AsyncClient, auth_headers: dict[str, str], session_id: str
) -> None:
    """실패 후 재검증 사이클: Run1 실패 → integrating → validating → Run2 통과."""
    # Run 1: 보안 미달 → 실패
    r1 = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={"threshold": 70},
        headers=auth_headers,
    )
    rid1 = r1.json()["id"]

    await client.post(
        f"/api/v1/quality-gate/runs/{rid1}/checks",
        json={"category": "code_quality", "score": 80},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{rid1}/checks",
        json={"category": "security", "score": 40},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{rid1}/evaluate",
        json={"auto_transition": True},
        headers=auth_headers,
    )

    # 세션 → integrating
    sess = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}",
        headers=auth_headers,
    )
    assert sess.json()["phase"] == "integrating"

    # 재작업 후 다시 validating으로 전이
    await client.put(
        f"/api/v1/orchestrator/sessions/{session_id}/transition",
        json={"target_phase": "validating"},
        headers=auth_headers,
    )

    # Run 2: 모두 통과
    r2 = await client.post(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        json={"threshold": 70},
        headers=auth_headers,
    )
    assert r2.json()["run_number"] == 2
    rid2 = r2.json()["id"]

    await client.post(
        f"/api/v1/quality-gate/runs/{rid2}/checks",
        json={"category": "code_quality", "score": 85},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{rid2}/checks",
        json={"category": "security", "score": 80},
        headers=auth_headers,
    )
    await client.post(
        f"/api/v1/quality-gate/runs/{rid2}/evaluate",
        json={"auto_transition": True},
        headers=auth_headers,
    )

    # 세션 → approved
    sess = await client.get(
        f"/api/v1/orchestrator/sessions/{session_id}",
        headers=auth_headers,
    )
    assert sess.json()["phase"] == "approved"

    # 실행 목록 확인 (2건)
    runs_resp = await client.get(
        f"/api/v1/quality-gate/sessions/{session_id}/runs",
        headers=auth_headers,
    )
    assert runs_resp.json()["total"] == 2
