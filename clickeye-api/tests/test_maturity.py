"""성숙도 평가 API 테스트 (질문지, 스코어링, 최근 평가 조회)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preset import Preset


async def _seed_preset(db: AsyncSession, level: str = "starter") -> Preset:
    """테스트용 프리셋 삽입."""
    preset = Preset(
        name=f"Test {level.capitalize()}",
        slug=f"test-{level}-{uuid.uuid4().hex[:8]}",
        maturity_level=level,
        solution_types=["web-app"],
        default_agents=["claude-code"],
        default_skills=["code-generation"],
        default_pipelines=["simple-build"],
        description=f"테스트용 {level} 프리셋",
        is_system=True,
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return preset


# ── 질문지 조회 (인증 불요) ──


@pytest.mark.asyncio
async def test_get_questions_no_auth(client: AsyncClient) -> None:
    """인증 없이 질문지 조회 가능."""
    resp = await client.get("/api/v1/maturity/questions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 7  # 최소 7개 질문


@pytest.mark.asyncio
async def test_questions_structure(client: AsyncClient) -> None:
    """질문지 구조 검증: id, text, category, weight, options."""
    resp = await client.get("/api/v1/maturity/questions")
    data = resp.json()
    q = data[0]
    assert "id" in q
    assert "text" in q
    assert "category" in q
    assert "weight" in q
    assert "options" in q
    assert isinstance(q["options"], list)
    assert len(q["options"]) >= 2


@pytest.mark.asyncio
async def test_questions_categories(client: AsyncClient) -> None:
    """질문지 카테고리가 5개(team, process, tooling, ci, ai) 포함."""
    resp = await client.get("/api/v1/maturity/questions")
    data = resp.json()
    categories = {q["category"] for q in data}
    assert categories == {"team", "process", "tooling", "ci", "ai"}


# ── 성숙도 평가 수행 ──


@pytest.mark.asyncio
async def test_assess_starter_level(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """낮은 점수 응답 -> starter 레벨."""
    await _seed_preset(db_session, "starter")

    resp = await client.get("/api/v1/maturity/questions")
    questions = resp.json()
    answers = {q["id"]: q["options"][0]["score"] for q in questions}

    resp = await client.post(
        "/api/v1/maturity/assess",
        json={"answers": answers},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["level"] == "starter"
    assert 0 <= data["score"] <= 40
    assert "reasoning" in data


@pytest.mark.asyncio
async def test_assess_advanced_level(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """높은 점수 응답 -> advanced 레벨."""
    await _seed_preset(db_session, "advanced")

    resp = await client.get("/api/v1/maturity/questions")
    questions = resp.json()
    answers = {q["id"]: q["options"][-1]["score"] for q in questions}

    resp = await client.post(
        "/api/v1/maturity/assess",
        json={"answers": answers},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["level"] == "advanced"
    assert data["score"] >= 70


@pytest.mark.asyncio
async def test_assess_intermediate_level(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """중간 점수 -> intermediate 레벨."""
    await _seed_preset(db_session, "intermediate")

    resp = await client.get("/api/v1/maturity/questions")
    questions = resp.json()
    # 중간 옵션 선택 (각 질문의 두 번째 옵션)
    answers = {q["id"]: q["options"][1]["score"] for q in questions}

    resp = await client.post(
        "/api/v1/maturity/assess",
        json={"answers": answers},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["level"] == "intermediate"
    assert 40 <= data["score"] < 70


@pytest.mark.asyncio
async def test_assess_empty_answers(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """빈 응답은 422 유효성 실패."""
    resp = await client.post(
        "/api/v1/maturity/assess",
        json={"answers": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_assess_without_auth(client: AsyncClient) -> None:
    """인증 없이 평가 수행 시 401."""
    resp = await client.post(
        "/api/v1/maturity/assess",
        json={"answers": {"team-size": 50}},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_assess_returns_preset_recommendation(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """평가 결과에 추천 프리셋 ID가 포함."""
    preset = await _seed_preset(db_session, "starter")

    resp = await client.get("/api/v1/maturity/questions")
    questions = resp.json()
    answers = {q["id"]: q["options"][0]["score"] for q in questions}

    resp = await client.post(
        "/api/v1/maturity/assess",
        json={"answers": answers},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["recommended_preset_id"] == str(preset.id)


# ── 스코어링 알고리즘 정확성 ──


@pytest.mark.asyncio
async def test_scoring_weighted_average(client: AsyncClient) -> None:
    """가중 평균 스코어링이 정확한지 단위 검증."""
    from app.schemas.preset import MaturityQuestion
    from app.services.maturity_service import _calculate_score

    questions = [
        MaturityQuestion(
            id="q1",
            text="Q1",
            category="team",
            weight=2.0,
            options=[{"label": "A", "score": 10}],
        ),
        MaturityQuestion(
            id="q2",
            text="Q2",
            category="process",
            weight=1.0,
            options=[{"label": "A", "score": 10}],
        ),
    ]

    # weight 2.0 * score 100 + weight 1.0 * score 50 = 250 / 3.0 ≈ 83
    answers = {"q1": 100, "q2": 50}
    score = _calculate_score(answers, questions)
    assert score == 83  # round(250 / 3.0) = 83

    # weight 2.0 * score 0 + weight 1.0 * score 100 = 100 / 3.0 ≈ 33
    answers2 = {"q1": 0, "q2": 100}
    score2 = _calculate_score(answers2, questions)
    assert score2 == 33  # round(100 / 3.0) = 33


@pytest.mark.asyncio
async def test_scoring_level_boundaries() -> None:
    """점수 경계값 매핑 정확성."""
    from app.services.maturity_service import _score_to_level

    assert _score_to_level(0) == "starter"
    assert _score_to_level(39) == "starter"
    assert _score_to_level(40) == "intermediate"
    assert _score_to_level(69) == "intermediate"
    assert _score_to_level(70) == "advanced"
    assert _score_to_level(100) == "advanced"


# ── 최근 평가 조회 (GET /me) ──


@pytest.mark.asyncio
async def test_get_my_assessment_empty(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """평가 기록 없을 때 404."""
    resp = await client.get("/api/v1/maturity/me", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_my_assessment_after_assess(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """평가 수행 후 /me로 결과 조회."""
    await _seed_preset(db_session, "starter")

    resp = await client.get("/api/v1/maturity/questions")
    questions = resp.json()
    answers = {q["id"]: q["options"][0]["score"] for q in questions}

    # 평가 수행
    await client.post(
        "/api/v1/maturity/assess",
        json={"answers": answers},
        headers=auth_headers,
    )

    # 결과 조회
    resp = await client.get("/api/v1/maturity/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["level"] == "starter"
    assert "score" in data
    assert "answers" in data
    assert "created_at" in data
    assert "id" in data


@pytest.mark.asyncio
async def test_get_my_assessment_without_auth(client: AsyncClient) -> None:
    """인증 없이 /me 조회 시 401."""
    resp = await client.get("/api/v1/maturity/me")
    assert resp.status_code in (401, 403)


# ── 회원가입 시 maturity_required 플래그 ──


@pytest.mark.asyncio
async def test_register_returns_maturity_required(client: AsyncClient) -> None:
    """회원가입 응답에 maturity_required=True 포함."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "maturity@example.com",
            "password": "testpassword123",
            "display_name": "성숙도 테스트",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["maturity_required"] is True
