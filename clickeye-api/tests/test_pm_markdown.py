"""PM Markdown 직렬화/파싱 서비스 테스트.

단위 테스트: serialize_pm_to_markdown / parse_markdown_to_pm_dict
통합 테스트: GET/PUT /pm-profiles/{id}/markdown 엔드포인트
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pm_profile import PMProfile
from app.models.user import User
from app.services.pm_markdown_service import parse_markdown_to_pm_dict, serialize_pm_to_markdown

# ─── 헬퍼 ───────────────────────────────────────────────────────────────────


def _make_profile(**kwargs) -> PMProfile:  # type: ignore[no-untyped-def]
    """테스트용 PMProfile 인스턴스를 생성한다 (DB 저장 없음)."""
    defaults = dict(
        id=uuid.uuid4(),
        name="김제품",
        slug="kim-product",
        title="제품 전략 PM",
        description="제품 전략 전문가",
        domain="product",
        years_experience=5,
        language="ko",
        is_active=True,
        specialties=["roadmap", "user-research"],
        tech_stack_tags=["python", "react"],
        industry_tags=["fintech"],
        preferred_solution_types=["saas"],
        bio_long="10년 경력의 시니어 PM입니다.",
        personality={},
    )
    defaults.update(kwargs)
    return PMProfile(**defaults)


async def _register_and_login(
    client: AsyncClient,
    email: str = "admin@example.com",
    password: str = "adminpass123",
) -> tuple[dict[str, str], str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "display_name": "관리자"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    token = resp.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return {"Authorization": f"Bearer {token}"}, me.json()["id"]


async def _set_role(db: AsyncSession, user_id: str, role: str) -> None:
    stmt = update(User).where(User.id == uuid.UUID(user_id)).values(system_role=role)
    await db.execute(stmt)
    await db.commit()


async def _seed_profile(db: AsyncSession) -> str:
    profile = _make_profile()
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return str(profile.id)


# ─── 단위 테스트: serialize_pm_to_markdown ───────────────────────────────────


def test_serialize_has_frontmatter() -> None:
    profile = _make_profile()
    md = serialize_pm_to_markdown(profile)
    assert md.startswith("---\n")
    assert "\n---" in md


def test_serialize_frontmatter_fields() -> None:
    profile = _make_profile()
    md = serialize_pm_to_markdown(profile)
    assert "name:" in md
    assert "slug:" in md
    assert "language:" in md
    assert "specialties:" in md


def test_serialize_description_in_body() -> None:
    profile = _make_profile(description="설명 텍스트")
    md = serialize_pm_to_markdown(profile)
    assert "설명 텍스트" in md


def test_serialize_bio_long_with_separator() -> None:
    profile = _make_profile(bio_long="상세 소개입니다.")
    md = serialize_pm_to_markdown(profile)
    assert "---bio---" in md
    assert "상세 소개입니다." in md


def test_serialize_no_bio_no_separator() -> None:
    profile = _make_profile(bio_long=None)
    md = serialize_pm_to_markdown(profile)
    assert "---bio---" not in md


# ─── 단위 테스트: parse_markdown_to_pm_dict ──────────────────────────────────


def test_parse_returns_dict() -> None:
    md = "---\nname: 테스트\nslug: test\n---\n\n설명입니다.\n"
    result = parse_markdown_to_pm_dict(md)
    assert isinstance(result, dict)


def test_parse_extracts_name() -> None:
    md = "---\nname: 홍길동\nslug: hong\n---\n"
    result = parse_markdown_to_pm_dict(md)
    assert result.get("name") == "홍길동"


def test_parse_extracts_list_fields() -> None:
    md = "---\nname: x\nslug: x\nspecialties:\n  - a\n  - b\n---\n"
    result = parse_markdown_to_pm_dict(md)
    assert result.get("specialties") == ["a", "b"]


def test_parse_extracts_description_from_body() -> None:
    md = "---\nname: x\nslug: x\n---\n\n본문 설명입니다.\n"
    result = parse_markdown_to_pm_dict(md)
    assert result.get("description") == "본문 설명입니다."


def test_parse_splits_bio_on_separator() -> None:
    md = "---\nname: x\nslug: x\n---\n\n설명\n\n---bio---\n\n상세소개\n"
    result = parse_markdown_to_pm_dict(md)
    assert result.get("description") == "설명"
    assert result.get("bio_long") == "상세소개"


def test_parse_invalid_yaml_frontmatter_fallback() -> None:
    md = "---\n: : invalid yaml :::\n---\n\n설명\n"
    result = parse_markdown_to_pm_dict(md)
    # YAML 파싱 실패해도 dict를 반환한다
    assert isinstance(result, dict)


# ─── 단위 테스트: 라운드트립 ──────────────────────────────────────────────────


def test_roundtrip_serialize_parse_serialize() -> None:
    """serialize(parse(serialize(pm))) == serialize(pm) 라운드트립."""
    original = _make_profile()
    first_md = serialize_pm_to_markdown(original)

    parsed_dict = parse_markdown_to_pm_dict(first_md)
    # 파싱 결과로 새 프로필 구성 (slug는 URL 기반이므로 원본 유지)
    reconstructed = _make_profile(
        **{k: v for k, v in parsed_dict.items() if v is not None and k != "slug"}
    )
    second_md = serialize_pm_to_markdown(reconstructed)

    assert second_md == first_md


def test_roundtrip_preserves_name() -> None:
    profile = _make_profile(name="이름보존테스트")
    md = serialize_pm_to_markdown(profile)
    parsed = parse_markdown_to_pm_dict(md)
    assert parsed.get("name") == "이름보존테스트"


def test_roundtrip_preserves_specialties() -> None:
    profile = _make_profile(specialties=["alpha", "beta", "gamma"])
    md = serialize_pm_to_markdown(profile)
    parsed = parse_markdown_to_pm_dict(md)
    assert parsed.get("specialties") == ["alpha", "beta", "gamma"]


# ─── 통합 테스트: GET /pm-profiles/{id}/markdown ────────────────────────────


@pytest.mark.asyncio
async def test_get_markdown_returns_text_plain(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, user_id = await _register_and_login(client)
    await _set_role(db_session, user_id, "admin")
    profile_id = await _seed_profile(db_session)

    resp = await client.get(
        f"/api/v1/pm-profiles/{profile_id}/markdown",
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert resp.text.startswith("---\n")


@pytest.mark.asyncio
async def test_get_markdown_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, user_id = await _register_and_login(client)
    await _set_role(db_session, user_id, "admin")

    resp = await client.get(
        "/api/v1/pm-profiles/00000000-0000-0000-0000-000000000000/markdown",
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_markdown_requires_permission(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    profile_id = await _seed_profile(db_session)
    resp = await client.get(
        f"/api/v1/pm-profiles/{profile_id}/markdown",
        headers=auth_headers,
    )
    assert resp.status_code == 403


# ─── 통합 테스트: PUT /pm-profiles/{id}/markdown ────────────────────────────


@pytest.mark.asyncio
async def test_put_markdown_updates_profile(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, user_id = await _register_and_login(client)
    await _set_role(db_session, user_id, "admin")
    profile_id = await _seed_profile(db_session)

    new_md = (
        "---\n"
        "name: 업데이트된 이름\n"
        "slug: kim-product\n"
        "title: 새 직함\n"
        "language: ko\n"
        "is_active: true\n"
        "specialties:\n"
        "  - new-skill\n"
        "tech_stack_tags: []\n"
        "industry_tags: []\n"
        "preferred_solution_types: []\n"
        "---\n\n"
        "업데이트된 설명입니다.\n"
    )
    resp = await client.put(
        f"/api/v1/pm-profiles/{profile_id}/markdown",
        content=new_md,
        headers={**headers, "content-type": "text/plain"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "업데이트된 이름"
    assert body["title"] == "새 직함"
    assert body["description"] == "업데이트된 설명입니다."
    assert "new-skill" in body["specialties"]


@pytest.mark.asyncio
async def test_put_markdown_stores_markdown_body(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, user_id = await _register_and_login(client)
    await _set_role(db_session, user_id, "admin")
    profile_id = await _seed_profile(db_session)

    new_md = (
        "---\n"
        "name: 저장 테스트\n"
        "slug: kim-product\n"
        "language: ko\n"
        "is_active: true\n"
        "specialties: []\n"
        "tech_stack_tags: []\n"
        "industry_tags: []\n"
        "preferred_solution_types: []\n"
        "---\n\n"
        "markdown_body 저장 확인용 설명.\n"
    )
    resp = await client.put(
        f"/api/v1/pm-profiles/{profile_id}/markdown",
        content=new_md,
        headers={**headers, "content-type": "text/plain"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # markdown_body 필드가 응답에 포함되어야 한다
    assert "markdown_body" in body
    assert body["markdown_body"] == new_md


@pytest.mark.asyncio
async def test_put_markdown_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    headers, user_id = await _register_and_login(client)
    await _set_role(db_session, user_id, "admin")

    resp = await client.put(
        "/api/v1/pm-profiles/00000000-0000-0000-0000-000000000000/markdown",
        content="---\nname: x\nslug: y\n---\n",
        headers={**headers, "content-type": "text/plain"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_markdown_requires_permission(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    profile_id = await _seed_profile(db_session)
    resp = await client.put(
        f"/api/v1/pm-profiles/{profile_id}/markdown",
        content="---\nname: x\nslug: y\n---\n",
        headers={**auth_headers, "content-type": "text/plain"},
    )
    assert resp.status_code == 403
