import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def _create_org(client: AsyncClient, headers: dict[str, str]) -> str:
    """테스트용 조직을 생성하고 ID를 반환한다."""
    resp = await client.post(
        "/api/v1/organizations/",
        json={"company_name": "테스트 회사", "size": "11-50", "industry": "IT"},
        headers=headers,
    )
    return resp.json()["id"]


async def _create_session(
    client: AsyncClient, headers: dict[str, str], org_id: str
) -> dict:
    """테스트용 프로토타입 세션을 생성한다."""
    resp = await client.post(
        "/api/v1/prototype-sessions/",
        json={
            "organization_id": org_id,
            "solution_prompt": "SaaS 구독 관리 서비스를 만들고 싶습니다",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_start_generation_atomic_guard(
    client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
) -> None:
    """동시 중복 generate로 인한 배치 중복 실행을 막는 원자적 재진입 가드 검증.

    - 1회차: pending → generating
    - 2회차(동일 세션): 이미 generating → ALREADY_GENERATED(409)
    - 미존재 세션: SESSION_NOT_FOUND(404)
    엔드포인트는 live_preview 503 게이트로 막히므로 서비스 레벨에서 직접 검증한다.
    """
    from app.core.exceptions import AppError
    from app.models.prototype_session import PrototypeSession
    from app.services.prototype_service import PrototypeService

    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)
    row = await db_session.get(PrototypeSession, uuid.UUID(session["id"]))
    assert row is not None

    svc = PrototypeService(db_session)

    first = await svc.start_generation(row.id, row.user_id)
    assert first.status == "generating"

    with pytest.raises(AppError) as exc_dup:
        await svc.start_generation(row.id, row.user_id)
    assert exc_dup.value.status_code == 409
    assert exc_dup.value.code == "ALREADY_GENERATED"

    with pytest.raises(AppError) as exc_missing:
        await svc.start_generation(uuid.uuid4(), row.user_id)
    assert exc_missing.value.status_code == 404


@pytest.mark.asyncio
async def test_create_session(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    body = await _create_session(client, auth_headers, org_id)
    assert body["status"] == "pending"
    assert body["organization_id"] == org_id
    assert body["solution_prompt"] == "SaaS 구독 관리 서비스를 만들고 싶습니다"
    assert body["current_step"] == 1


@pytest.mark.asyncio
async def test_create_session_unauthenticated(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/prototype-sessions/",
        json={
            "organization_id": "00000000-0000-0000-0000-000000000000",
            "solution_prompt": "테스트",
        },
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_sessions(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    await _create_session(client, auth_headers, org_id)
    await _create_session(client, auth_headers, org_id)

    resp = await client.get(
        "/api/v1/prototype-sessions/", headers=auth_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_get_session(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}", headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == session["id"]


@pytest.mark.asyncio
async def test_get_session_not_found(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    resp = await client.get(
        "/api/v1/prototype-sessions/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_session_status(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/status",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_generate_prototypes(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    # 생성 시작 → 202 Accepted
    resp = await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes/generate",
        headers=auth_headers,
    )
    assert resp.status_code == 202
    body = resp.json()
    assert body["task_id"] == session["id"]
    assert body["session_id"] == session["id"]
    assert body["status"] == "generating"
    assert body["message"] == "프로토타입 생성이 시작되었습니다"

    # BackgroundTask가 완료된 후 상태 확인 (테스트 환경에서 동기 실행)
    status_resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/status",
        headers=auth_headers,
    )
    assert status_resp.json()["status"] == "completed"

    # 프로토타입 목록 확인
    proto_resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes",
        headers=auth_headers,
    )
    assert proto_resp.status_code == 200
    prototypes = proto_resp.json()
    assert prototypes["total"] >= 1
    first = prototypes["items"][0]
    assert first["title"] is not None
    assert first["status"] == "ready"
    assert first["variant_index"] == 0


@pytest.mark.asyncio
async def test_generate_prototypes_duplicate(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    # 첫 번째 생성 시작
    await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes/generate",
        headers=auth_headers,
    )

    # 중복 생성 시도 (이미 generating 또는 completed 상태)
    resp = await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes/generate",
        headers=auth_headers,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_list_prototypes(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    # 생성 시작 (백그라운드 완료 대기)
    gen_resp = await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes/generate",
        headers=auth_headers,
    )
    assert gen_resp.status_code == 202

    resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert len(body["items"]) >= 1


@pytest.mark.asyncio
async def test_select_prototype(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    # 생성 시작 (백그라운드 완료 대기)
    await client.post(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes/generate",
        headers=auth_headers,
    )

    # 프로토타입 목록 조회
    proto_resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}/prototypes",
        headers=auth_headers,
    )
    prototype_id = proto_resp.json()["items"][0]["id"]

    # PATCH로 프로토타입 선택
    resp = await client.patch(
        f"/api/v1/prototype-sessions/{session['id']}",
        json={"selected_prototype_id": prototype_id},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    # 선택된 세션 응답 확인
    assert resp.json()["selected_prototype_id"] == prototype_id


@pytest.mark.asyncio
async def test_delete_session(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    org_id = await _create_org(client, auth_headers)
    session = await _create_session(client, auth_headers, org_id)

    resp = await client.delete(
        f"/api/v1/prototype-sessions/{session['id']}", headers=auth_headers
    )
    assert resp.status_code == 204

    # 삭제 후 조회 시 404
    get_resp = await client.get(
        f"/api/v1/prototype-sessions/{session['id']}", headers=auth_headers
    )
    assert get_resp.status_code == 404
