"""백엔드 API 통합 테스트 (P2 fix_plan 24S-43).

검증 범위:
- 카탈로그 API: 에이전트/스킬/플랫폼/파이프라인 상세 응답 구조 + ID 고유성
- Organization API: CRUD 전체 동작 (생성/조회/upsert 수정/유효성/인증)
- 프리뷰 API: 위저드 설정 → 파일 트리 구조 일관성 + 리프 노드 매칭
- ZIP 생성 API: 파일 내용 검증 + .env 포함/미포함 + settings.json 구조
- 추천 API: 솔루션 유형별 추천 결과 (에이전트/스킬/파이프라인) + 카탈로그 참조 무결성
- ProjectConfig: 저장/조회/덮어쓰기/미인증/404 + generate 자동 저장 + 재다운로드 연계
"""

import json
import uuid
import zipfile
from io import BytesIO

import pytest
from httpx import AsyncClient

# ── 헬퍼 ──


async def _create_project(
    client: AsyncClient, headers: dict[str, str], name: str = "통합 테스트"
) -> str:
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": name},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _auth_and_project(
    client: AsyncClient, name: str = "통합 테스트"
) -> tuple[dict[str, str], str]:
    """독립 유저 생성 + 프로젝트 생성 → (auth_headers, project_id)."""
    email = f"integ-{uuid.uuid4().hex[:8]}@test.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "display_name": "통합"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    project_id = await _create_project(client, headers, name)
    return headers, project_id


def _open_zip(content: bytes) -> zipfile.ZipFile:
    buf = BytesIO(content)
    assert zipfile.is_zipfile(buf)
    buf.seek(0)
    return zipfile.ZipFile(buf)


# ═══════════════════════════════════════════════════════════════
#  1. 카탈로그 응답 구조 상세 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_catalog_agents_response_structure(
    client: AsyncClient, seeded_catalog: None
) -> None:
    """에이전트 카탈로그: 각 항목에 id, label, description 포함 + 7개 항목."""
    resp = await client.get("/api/v1/catalog/agents")
    assert resp.status_code == 200

    data = resp.json()
    assert data["total"] == 7
    for agent in data["items"]:
        assert isinstance(agent["id"], str) and len(agent["id"]) > 0
        assert isinstance(agent["label"], str) and len(agent["label"]) > 0
        assert isinstance(agent.get("description", ""), str)


@pytest.mark.asyncio
async def test_catalog_skills_have_type_field(
    client: AsyncClient, seeded_catalog: None
) -> None:
    """스킬 카탈로그: 각 항목에 id, label, description 포함 + 6개 항목."""
    resp = await client.get("/api/v1/catalog/skills")
    data = resp.json()

    assert data["total"] == 6
    for skill in data["items"]:
        assert isinstance(skill["id"], str) and len(skill["id"]) > 0
        assert isinstance(skill["label"], str) and len(skill["label"]) > 0
        assert isinstance(skill.get("description", ""), str)


@pytest.mark.asyncio
async def test_catalog_platforms_have_config_fields(client: AsyncClient) -> None:
    """플랫폼 카탈로그: config_dir, agent_file, env_vars 필드 존재."""
    resp = await client.get("/api/v1/catalog/platforms")
    data = resp.json()

    for platform in data["items"]:
        assert isinstance(platform["id"], str) and len(platform["id"]) > 0
        assert isinstance(platform["name"], str) and len(platform["name"]) > 0
        assert "config_dir" in platform
        assert "agent_file" in platform
        assert platform["config_dir"].startswith(".")
        assert isinstance(platform.get("env_vars", []), list)


@pytest.mark.asyncio
async def test_catalog_pipelines_have_steps(client: AsyncClient) -> None:
    """파이프라인 카탈로그: steps 필드가 비어있지 않은 리스트."""
    resp = await client.get("/api/v1/catalog/pipelines")
    data = resp.json()

    for pipeline in data["items"]:
        assert isinstance(pipeline["id"], str) and len(pipeline["id"]) > 0
        assert isinstance(pipeline["name"], str) and len(pipeline["name"]) > 0
        assert "steps" in pipeline
        assert isinstance(pipeline["steps"], list)
        assert len(pipeline["steps"]) > 0


@pytest.mark.asyncio
async def test_catalog_ids_unique_within_type(
    client: AsyncClient, seeded_catalog: None
) -> None:
    """각 카탈로그 타입 내에서 id가 고유한지 검증."""
    for endpoint in ("agents", "skills", "platforms", "pipelines"):
        resp = await client.get(f"/api/v1/catalog/{endpoint}")
        items = resp.json()["items"]
        ids = [item["id"] for item in items]
        assert len(ids) == len(set(ids)), f"{endpoint}에 중복 id 존재: {ids}"


# ═══════════════════════════════════════════════════════════════
#  2. 카탈로그 → 추천 → 프리뷰 → ZIP 연계 흐름
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_catalog_ids_used_in_preview(
    client: AsyncClient, auth_headers: dict[str, str], seeded_catalog: None
) -> None:
    """카탈로그 에이전트/스킬 ID로 프리뷰 요청 시 해당 파일 생성."""
    # 카탈로그에서 에이전트/스킬 ID 조회
    agents_resp = await client.get("/api/v1/catalog/agents")
    skills_resp = await client.get("/api/v1/catalog/skills")

    catalog_agent_ids = [a["id"] for a in agents_resp.json()["items"]]
    catalog_skill_ids = [s["id"] for s in skills_resp.json()["items"]]

    # 엔진이 인식하는 에이전트 ID만 필터
    engine_agents = [
        aid for aid in catalog_agent_ids
        if aid in ("backend", "frontend", "uiux", "devops", "fullstack")
    ]
    # 엔진이 인식하는 스킬 ID만 필터
    engine_skills = [
        sid for sid in catalog_skill_ids
        if sid in ("tdd", "ai-critique", "ralph-loop", "harness-gate", "linear")
    ]

    project_id = await _create_project(client, auth_headers, "카탈로그 연계")
    resp = await client.post(
        f"/api/v1/projects/{project_id}/preview",
        json={
            "solution": {
                "projectName": "catalog-test",
                "solutionType": "fullstack",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": engine_agents[:2],
            "skills": engine_skills[:2],
            "platform": {"platformId": "claude-code"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    files = resp.json()["files"]
    assert len(files) > 0
    # 선택한 에이전트/스킬 파일이 프리뷰에 포함
    assert any("agents/" in f for f in files)


# ═══════════════════════════════════════════════════════════════
#  3. Organization + ProjectConfig 연계
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_org_registration_then_wizard_flow(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """조직 등록 → 프로젝트 생성 → 위저드 설정 저장/조회 전체 흐름."""
    # 조직 등록
    org_resp = await client.post(
        "/api/v1/organizations/",
        json={
            "company_name": "통합 테스트 회사",
            "size": "11-50",
            "industry": "IT",
            "tech_stack": ["Python", "TypeScript"],
        },
        headers=auth_headers,
    )
    assert org_resp.status_code == 201
    assert org_resp.json()["company_name"] == "통합 테스트 회사"

    # 프로젝트 생성
    project_id = await _create_project(client, auth_headers, "조직 연계 테스트")

    # 위저드 설정 저장
    wizard_data = {
        "wizard_data": {
            "organization": {"name": "통합 테스트 회사", "size": "11-50"},
            "solution": {"type": "saas", "description": "통합 테스트용"},
            "agents": [{"id": "backend"}, {"id": "frontend"}],
            "skills": [{"id": "tdd"}],
            "pipelines": [{"id": "harness"}],
            "platform": {"target": "claude-code"},
        }
    }
    save_resp = await client.post(
        f"/api/v1/projects/{project_id}/config",
        json=wizard_data,
        headers=auth_headers,
    )
    assert save_resp.status_code == 200

    # 설정 조회 → 저장한 내용과 일치
    get_resp = await client.get(
        f"/api/v1/projects/{project_id}/config",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    saved = get_resp.json()["wizard_data"]
    assert saved["organization"]["name"] == "통합 테스트 회사"
    assert len(saved["agents"]) == 2
    assert saved["platform"]["target"] == "claude-code"


# ═══════════════════════════════════════════════════════════════
#  4. 프리뷰 → ZIP 파일 일관성
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_preview_and_zip_file_consistency(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """프리뷰 파일 목록과 ZIP 파일 목록이 정확히 일치 (env_vars 없을 때)."""
    project_id = await _create_project(client, auth_headers, "일관성 테스트")
    payload = {
        "solution": {
            "projectName": "consistency-app",
            "solutionType": "fullstack",
            "stackPreset": "fastapi-nextjs",
        },
        "agents": ["backend", "frontend"],
        "skills": ["tdd", "ralph-loop"],
        "platform": {"platformId": "claude-code"},
    }

    # 프리뷰
    preview_resp = await client.post(
        f"/api/v1/projects/{project_id}/preview",
        json=payload,
        headers=auth_headers,
    )
    assert preview_resp.status_code == 200
    preview_files = set(preview_resp.json()["files"].keys())

    # ZIP (env_vars 없이)
    gen_resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json=payload,
        headers=auth_headers,
    )
    assert gen_resp.status_code == 200
    zip_files = set(_open_zip(gen_resp.content).namelist())

    assert preview_files == zip_files, (
        f"프리뷰 전용: {preview_files - zip_files}, "
        f"ZIP 전용: {zip_files - preview_files}"
    )


@pytest.mark.asyncio
async def test_preview_file_tree_matches_files(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """프리뷰 file_tree의 리프 노드가 files 키와 일치."""
    project_id = await _create_project(client, auth_headers, "트리 매칭")
    resp = await client.post(
        f"/api/v1/projects/{project_id}/preview",
        json={
            "solution": {
                "projectName": "tree-test",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": ["backend"],
            "skills": [],
            "platform": {"platformId": "claude-code"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()

    # file_tree에서 리프 노드(file 타입) 경로 수집
    def _collect_leaves(nodes: list[dict]) -> set[str]:
        paths: set[str] = set()
        for node in nodes:
            if node["type"] == "file":
                paths.add(node["path"])
            if node.get("children"):
                paths |= _collect_leaves(node["children"])
        return paths

    tree_files = _collect_leaves(data["file_tree"])
    file_keys = set(data["files"].keys())
    assert tree_files == file_keys


# ═══════════════════════════════════════════════════════════════
#  5. ZIP 생성 → .env 검증 + 내용 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_zip_content_has_project_name(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """ZIP 내 CLAUDE.md에 프로젝트명과 스택 정보 반영."""
    project_id = await _create_project(client, auth_headers, "내용 검증")
    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {
                "projectName": "my-awesome-app",
                "solutionType": "webapp",
                "stackPreset": "django-react",
            },
            "agents": ["backend"],
            "skills": [],
            "platform": {"platformId": "claude-code"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        guide = zf.read("CLAUDE.md").decode()
        assert "my-awesome-app" in guide
        assert "Django" in guide


@pytest.mark.asyncio
async def test_zip_env_vars_isolation(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """ZIP의 .env에 실제 값, .env.example에는 키만 포함."""
    project_id = await _create_project(client, auth_headers, "ENV 격리")
    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {
                "projectName": "env-test",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": [],
            "skills": [],
            "platform": {"platformId": "claude-code"},
            "env_vars": {
                "SECRET_KEY": "super-secret-123",
                "DB_URL": "postgres://localhost/db",
            },
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        env = zf.read(".env").decode()
        example = zf.read(".env.example").decode()

        # .env에 실제 값 포함
        assert "SECRET_KEY=super-secret-123" in env
        assert "DB_URL=postgres://localhost/db" in env

        # .env.example에 키만
        assert "SECRET_KEY=" in example
        assert "super-secret-123" not in example
        assert "DB_URL=" in example
        assert "postgres://localhost/db" not in example


@pytest.mark.asyncio
async def test_zip_settings_json_structure(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """ZIP 내 settings.json이 플랫폼별 올바른 구조."""
    project_id = await _create_project(client, auth_headers, "설정 구조")
    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {
                "projectName": "settings-test",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": ["backend"],
            "skills": ["harness-gate"],
            "platform": {"platformId": "claude-code"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        settings = json.loads(zf.read(".claude/settings.json"))
        assert "permissions" in settings
        assert "allow" in settings["permissions"]
        assert "deny" in settings["permissions"]
        assert "hooks" in settings


# ═══════════════════════════════════════════════════════════════
#  6. 추천 → ZIP 생성 연계
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
#  7. ProjectConfig 저장 → 재다운로드 연계
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_config_save_via_generate_then_redownload(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """ZIP 생성(자동 설정 저장) → 재다운로드 시 동일 구조 + 새 env_vars 반영."""
    project_id = await _create_project(client, auth_headers, "재다운로드 연계")

    # ZIP 생성 (설정 자동 저장)
    gen_resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {
                "projectName": "redown-app",
                "solutionType": "fullstack",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": ["backend"],
            "skills": ["tdd"],
            "platform": {"platformId": "claude-code"},
            "env_vars": {"API_KEY": "old-key"},
        },
        headers=auth_headers,
    )
    assert gen_resp.status_code == 200

    # 설정 자동 저장 확인
    config_resp = await client.get(
        f"/api/v1/projects/{project_id}/config", headers=auth_headers
    )
    assert config_resp.status_code == 200
    assert config_resp.json()["wizard_data"] is not None

    # 재다운로드 (새 env_vars)
    redown_resp = await client.post(
        f"/api/v1/projects/{project_id}/redownload",
        json={"env_vars": {"API_KEY": "new-key-456"}},
        headers=auth_headers,
    )
    assert redown_resp.status_code == 200
    assert redown_resp.headers["content-type"] == "application/zip"

    with _open_zip(redown_resp.content) as zf:
        names = zf.namelist()
        # 원래 설정의 파일 구조 유지
        assert "CLAUDE.md" in names
        assert ".claude/agents/api-agent.md" in names
        assert ".claude/skills/tdd-smart-coding.md" in names

        # 새 env_vars 반영
        env = zf.read(".env").decode()
        assert "API_KEY=new-key-456" in env
        assert "old-key" not in env


@pytest.mark.asyncio
async def test_redownload_without_config_returns_error(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """위저드 설정 없이 재다운로드 시 에러."""
    project_id = await _create_project(client, auth_headers, "빈 설정 재다운로드")

    resp = await client.post(
        f"/api/v1/projects/{project_id}/redownload",
        json={"env_vars": {}},
        headers=auth_headers,
    )
    assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════
#  8. Organization CRUD 전체 흐름
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_organization_crud_full_flow(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """Organization 생성 → 조회 → upsert 수정 → 재조회 전체 CRUD."""
    # 생성
    create = await client.post(
        "/api/v1/organizations/",
        json={
            "company_name": "원래 회사",
            "size": "1-10",
            "industry": "교육",
            "tech_stack": ["Python"],
        },
        headers=auth_headers,
    )
    assert create.status_code == 201
    assert create.json()["company_name"] == "원래 회사"

    # 조회
    get1 = await client.get("/api/v1/organizations/me", headers=auth_headers)
    assert get1.status_code == 200
    assert get1.json()["tech_stack"] == ["Python"]

    # upsert 수정
    update = await client.post(
        "/api/v1/organizations/",
        json={
            "company_name": "변경 회사",
            "size": "51-200",
            "industry": "핀테크",
            "tech_stack": ["Python", "TypeScript", "Go"],
        },
        headers=auth_headers,
    )
    assert update.status_code == 201
    assert update.json()["company_name"] == "변경 회사"

    # 재조회 → 수정 값 반영 확인
    get2 = await client.get("/api/v1/organizations/me", headers=auth_headers)
    assert get2.status_code == 200
    body = get2.json()
    assert body["company_name"] == "변경 회사"
    assert body["size"] == "51-200"
    assert body["industry"] == "핀테크"
    assert body["tech_stack"] == ["Python", "TypeScript", "Go"]


# ═══════════════════════════════════════════════════════════════
#  9. 카탈로그 플랫폼 config_dir ↔ ZIP 구조 일관성
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_catalog_platform_config_dir_matches_zip(client: AsyncClient) -> None:
    """카탈로그의 config_dir이 실제 ZIP 디렉토리와 일치하는지 검증."""
    platforms_resp = await client.get("/api/v1/catalog/platforms")
    platforms = {p["id"]: p for p in platforms_resp.json()["items"]}

    headers, project_id = await _auth_and_project(client, "플랫폼 일관성")

    for pid, pdata in platforms.items():
        resp = await client.post(
            f"/api/v1/projects/{project_id}/generate",
            json={
                "solution": {"projectName": f"test-{pid}", "stackPreset": "fastapi-nextjs"},
                "agents": ["backend"],
                "skills": [],
                "platform": {"platformId": pid},
            },
            headers=headers,
        )
        assert resp.status_code == 200, f"플랫폼 {pid} ZIP 생성 실패"

        with _open_zip(resp.content) as zf:
            names = zf.namelist()
            config_dir = pdata["config_dir"] + "/"
            has_config_dir = any(n.startswith(config_dir) for n in names)
            assert has_config_dir, (
                f"플랫폼 {pid}: 카탈로그 config_dir={pdata['config_dir']}이 ZIP에 없음"
            )


# ═══════════════════════════════════════════════════════════════
#  10. 플랫폼별 settings.json 키 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform_id,required_keys",
    [
        ("claude-code", ["permissions", "hooks"]),
        ("gemini-cli", ["coreTools", "safetySettings"]),
        ("cursor", ["rules", "safetySettings"]),
    ],
    ids=["claude-code", "gemini-cli", "cursor"],
)
async def test_platform_settings_json_keys(
    client: AsyncClient,
    platform_id: str,
    required_keys: list[str],
) -> None:
    """각 플랫폼의 settings.json이 플랫폼 고유 키를 포함하는지 검증."""
    headers, project_id = await _auth_and_project(client, f"settings-{platform_id}")

    platforms_resp = await client.get("/api/v1/catalog/platforms")
    platform_data = next(
        p for p in platforms_resp.json()["items"] if p["id"] == platform_id
    )
    config_dir = platform_data["config_dir"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {"projectName": "settings-test", "stackPreset": "fastapi-nextjs"},
            "agents": ["backend"],
            "skills": [],
            "platform": {"platformId": platform_id},
        },
        headers=headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        settings_path = f"{config_dir}/settings.json"
        assert settings_path in zf.namelist()

        settings = json.loads(zf.read(settings_path))
        for key in required_keys:
            assert key in settings, (
                f"플랫폼 {platform_id}: settings.json에 '{key}' 키 없음"
            )


# ═══════════════════════════════════════════════════════════════
#  11. ProjectConfig 다중 덮어쓰기 일관성
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_config_multiple_overwrites(client: AsyncClient) -> None:
    """위저드 설정을 여러 번 덮어쓰고 마지막 값만 남는지 검증."""
    headers, project_id = await _auth_and_project(client, "다중 덮어쓰기")

    for i in range(1, 4):
        cfg = {
            "wizard_data": {
                "organization": {"name": f"회사 {i}"},
                "solution": {"type": "fullstack"},
                "agents": [{"id": "backend"}] * i,
                "skills": [],
                "pipelines": [],
                "platform": {"target": "claude-code"},
            }
        }
        resp = await client.post(
            f"/api/v1/projects/{project_id}/config",
            json=cfg,
            headers=headers,
        )
        assert resp.status_code == 200

    # 마지막 설정 반영 확인
    final = await client.get(
        f"/api/v1/projects/{project_id}/config", headers=headers
    )
    assert final.status_code == 200
    data = final.json()["wizard_data"]
    assert data["organization"]["name"] == "회사 3"
    assert len(data["agents"]) == 3


# ═══════════════════════════════════════════════════════════════
#  12. 추천 → 설정 저장 → 재다운로드 전체 연계
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
#  13. 모든 솔루션 유형 추천 → 카탈로그 참조 무결성
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
#  14. Organization 미인증/유효성 검증
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_organization_unauthenticated_access(client: AsyncClient) -> None:
    """인증 없이 Organization 생성/조회 시 401/403."""
    create_resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "인증 없음"},
    )
    assert create_resp.status_code in (401, 403)

    get_resp = await client.get("/api/v1/organizations/me")
    assert get_resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_organization_empty_name_rejected(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """빈 회사명은 422 에러."""
    resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_organization_not_found_before_create(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """조직 미등록 유저가 /me 조회 시 404."""
    resp = await client.get("/api/v1/organizations/me", headers=auth_headers)
    assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  15. ProjectConfig 독립 저장/조회 검증
# ═══════════════════════════════════════════════════════════════


WIZARD_CONFIG_SAMPLE = {
    "wizard_data": {
        "organization": {"name": "설정 테스트 조직", "size": "medium"},
        "solution": {"type": "saas", "description": "SaaS 프로젝트"},
        "agents": [{"id": "backend"}, {"id": "frontend"}],
        "skills": [{"id": "tdd"}, {"id": "code-review"}],
        "pipelines": [{"id": "harness"}, {"id": "lint-gate"}],
        "platform": {"platformId": "claude-code"},
    }
}


@pytest.mark.asyncio
async def test_config_explicit_save_and_retrieve(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """ProjectConfig 명시적 저장 후 조회 시 전체 데이터 일치."""
    project_id = await _create_project(client, auth_headers, "설정 직접 저장")

    # 저장
    save_resp = await client.post(
        f"/api/v1/projects/{project_id}/config",
        json=WIZARD_CONFIG_SAMPLE,
        headers=auth_headers,
    )
    assert save_resp.status_code == 200
    saved = save_resp.json()
    assert saved["project_id"] == project_id
    assert saved["wizard_data"]["organization"]["name"] == "설정 테스트 조직"
    assert saved["updated_at"] is not None

    # 조회
    get_resp = await client.get(
        f"/api/v1/projects/{project_id}/config",
        headers=auth_headers,
    )
    assert get_resp.status_code == 200
    retrieved = get_resp.json()
    assert retrieved["wizard_data"] == saved["wizard_data"]
    assert len(retrieved["wizard_data"]["agents"]) == 2
    assert len(retrieved["wizard_data"]["skills"]) == 2
    assert retrieved["wizard_data"]["platform"]["platformId"] == "claude-code"


@pytest.mark.asyncio
async def test_config_empty_before_save(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """설정 미저장 프로젝트의 config 조회 시 wizard_data가 None."""
    project_id = await _create_project(client, auth_headers, "빈 설정 조회")

    resp = await client.get(
        f"/api/v1/projects/{project_id}/config",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["wizard_data"] is None


@pytest.mark.asyncio
async def test_config_unauthenticated_access(client: AsyncClient) -> None:
    """인증 없이 설정 저장/조회 시 401/403."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    save_resp = await client.post(
        f"/api/v1/projects/{fake_id}/config",
        json=WIZARD_CONFIG_SAMPLE,
    )
    assert save_resp.status_code in (401, 403)

    get_resp = await client.get(f"/api/v1/projects/{fake_id}/config")
    assert get_resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_config_project_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """존재하지 않는 프로젝트에 설정 저장/조회 시 404."""
    fake_id = "00000000-0000-0000-0000-000000000099"

    save_resp = await client.post(
        f"/api/v1/projects/{fake_id}/config",
        json=WIZARD_CONFIG_SAMPLE,
        headers=auth_headers,
    )
    assert save_resp.status_code == 404

    get_resp = await client.get(
        f"/api/v1/projects/{fake_id}/config",
        headers=auth_headers,
    )
    assert get_resp.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  16. ZIP .env 미포함 확인 + 에이전트 파일 내용
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_zip_no_env_when_empty_env_vars(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    """env_vars가 빈 dict이면 .env 파일 미포함."""
    project_id = await _create_project(client, auth_headers, "ENV 미포함")
    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {"projectName": "no-env-app", "stackPreset": "custom"},
            "agents": [],
            "skills": [],
            "platform": {"platformId": "claude-code"},
            "env_vars": {},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        names = zf.namelist()
        assert ".env" not in names
        assert ".env.example" not in names


@pytest.mark.asyncio
async def test_zip_agent_file_contains_project_name(
    client: AsyncClient, auth_headers: dict[str, str], seeded_catalog: None
) -> None:
    """에이전트 파일(.claude/agents/api-agent.md)에 프로젝트명 반영."""
    project_id = await _create_project(client, auth_headers, "에이전트 내용 검증")
    resp = await client.post(
        f"/api/v1/projects/{project_id}/generate",
        json={
            "solution": {
                "projectName": "agent-name-test",
                "solutionType": "backend",
                "stackPreset": "fastapi-nextjs",
            },
            "agents": ["backend"],
            "skills": [],
            "platform": {"platformId": "claude-code"},
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200

    with _open_zip(resp.content) as zf:
        agent_md = zf.read(".claude/agents/api-agent.md").decode()
        assert "agent-name-test" in agent_md
        assert len(agent_md.strip()) > 0


# ═══════════════════════════════════════════════════════════════
#  17. 추천 솔루션 유형별 구체적 기대값 검증
# ═══════════════════════════════════════════════════════════════


