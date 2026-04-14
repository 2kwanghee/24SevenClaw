"""프리셋 카탈로그 + 성숙도 평가 API 테스트."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.preset import Preset


async def _seed_preset(db: AsyncSession) -> Preset:
    """테스트용 프리셋 직접 삽입."""
    preset = Preset(
        name="Test Starter",
        slug=f"test-starter-{uuid.uuid4().hex[:8]}",
        maturity_level="starter",
        solution_types=["web-app"],
        default_agents=["claude-code"],
        default_skills=["code-generation"],
        default_pipelines=["simple-build"],
        description="테스트용 프리셋",
        is_system=True,
    )
    db.add(preset)
    await db.commit()
    await db.refresh(preset)
    return preset


# ── 프리셋 목록 조회 ──


@pytest.mark.asyncio
async def test_list_presets_empty(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """프리셋이 없으면 빈 목록 반환."""
    resp = await client.get("/api/v1/presets/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_presets_with_data(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """프리셋이 있으면 목록 반환."""
    await _seed_preset(db_session)

    resp = await client.get("/api/v1/presets/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    item = data["items"][0]
    assert "id" in item
    assert "name" in item
    assert "slug" in item
    assert "maturity_level" in item


@pytest.mark.asyncio
async def test_list_presets_filter_maturity(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """maturity_level 필터 동작 확인."""
    await _seed_preset(db_session)

    resp = await client.get(
        "/api/v1/presets/?maturity_level=starter", headers=auth_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1

    # 없는 레벨 필터
    resp2 = await client.get(
        "/api/v1/presets/?maturity_level=advanced", headers=auth_headers
    )
    data2 = resp2.json()
    # seed한 것은 starter이므로 advanced에는 없어야 함
    for item in data2["items"]:
        assert item["maturity_level"] == "advanced"


@pytest.mark.asyncio
async def test_list_presets_unauthorized(client: AsyncClient) -> None:
    """인증 없이 프리셋 목록 조회 시 401."""
    resp = await client.get("/api/v1/presets/")
    assert resp.status_code in (401, 403)


# ── 프리셋 상세 조회 ──


@pytest.mark.asyncio
async def test_get_preset_by_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """프리셋 ID로 상세 조회."""
    preset = await _seed_preset(db_session)

    resp = await client.get(f"/api/v1/presets/{preset.id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(preset.id)
    assert data["name"] == "Test Starter"
    assert data["maturity_level"] == "starter"


@pytest.mark.asyncio
async def test_get_preset_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 프리셋 조회 시 404."""
    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/v1/presets/{fake_id}", headers=auth_headers)
    assert resp.status_code == 404


# ── 성숙도 평가 ──


@pytest.mark.asyncio
async def test_get_maturity_questions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """성숙도 질문지 조회."""
    resp = await client.get("/api/v1/presets/questions", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0

    q = data[0]
    assert "id" in q
    assert "text" in q
    assert "category" in q
    assert "weight" in q
    assert "options" in q


@pytest.mark.asyncio
async def test_assess_maturity_starter(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """낮은 점수 응답 → starter 레벨 평가."""
    await _seed_preset(db_session)

    # 모든 질문에 낮은 점수 응답
    resp = await client.get("/api/v1/presets/questions", headers=auth_headers)
    questions = resp.json()
    answers = {q["id"]: q["options"][0]["score"] for q in questions}

    resp = await client.post(
        "/api/v1/presets/assess",
        json={"answers": answers},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["level"] == "starter"
    assert 0 <= data["score"] <= 100
    assert "reasoning" in data


@pytest.mark.asyncio
async def test_assess_maturity_advanced(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """높은 점수 응답 → advanced 레벨 평가."""
    # advanced 프리셋도 시드
    advanced = Preset(
        name="Test Advanced",
        slug=f"test-advanced-{uuid.uuid4().hex[:8]}",
        maturity_level="advanced",
        solution_types=["web-app"],
        default_agents=["claude-code", "gemini-cli"],
        default_skills=["code-generation", "security-audit"],
        default_pipelines=["ci-cd-advanced"],
        description="테스트용 고급 프리셋",
        is_system=True,
    )
    db_session.add(advanced)
    await db_session.commit()

    # 모든 질문에 최고 점수 응답
    resp = await client.get("/api/v1/presets/questions", headers=auth_headers)
    questions = resp.json()
    answers = {q["id"]: q["options"][-1]["score"] for q in questions}

    resp = await client.post(
        "/api/v1/presets/assess",
        json={"answers": answers},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["level"] == "advanced"
    assert data["score"] >= 70


@pytest.mark.asyncio
async def test_assess_maturity_empty_answers(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """빈 응답은 유효성 검사 실패."""
    resp = await client.post(
        "/api/v1/presets/assess",
        json={"answers": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 422


# ── 프리셋 적용 ──


@pytest.mark.asyncio
async def test_apply_preset_to_project(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """프리셋을 프로젝트에 적용."""
    preset = await _seed_preset(db_session)

    # 프로젝트 생성
    proj_resp = await client.post(
        "/api/v1/projects/",
        json={"name": "적용 테스트 프로젝트"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 프리셋 적용
    resp = await client.post(
        f"/api/v1/presets/{preset.id}/apply?project_id={project_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert data["preset_id"] == str(preset.id)
    assert data["applied_agents"] == ["claude-code"]


@pytest.mark.asyncio
async def test_apply_preset_no_project_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """project_id 없이 프리셋 적용 시 400."""
    preset = await _seed_preset(db_session)

    resp = await client.post(
        f"/api/v1/presets/{preset.id}/apply",
        headers=auth_headers,
    )
    assert resp.status_code == 400
