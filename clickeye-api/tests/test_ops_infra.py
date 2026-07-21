"""CE-305 PR-2 — superadmin 게이트 + 읽기 전용 인프라 조회 테스트."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.services.ops import docker_client, ops_audit, port_probe


async def _register_and_login(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pw12345678", "display_name": "t"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "pw12345678"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return headers, me.json()["id"]


async def _set_role(db: AsyncSession, user_id: str, role: str) -> None:
    await db.execute(update(User).where(User.id == uuid.UUID(user_id)).values(system_role=role))
    await db.commit()


@pytest.fixture
def ops_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """feature_ops_panel 플래그를 활성화 + docker/port 호출을 스텁으로 대체."""
    monkeypatch.setattr(settings, "feature_ops_panel", True)

    async def _fake_containers() -> list[dict[str, Any]]:
        return [
            {
                "name": "clickeye-api",
                "image": "clickeye-api:latest",
                "state": "running",
                "status": "Up 2 hours (healthy)",
                "health": "healthy",
                "ports": ["0.0.0.0:8000->8000/tcp"],
                "created": 1700000000,
            }
        ]

    async def _fake_ports() -> list[dict[str, object]]:
        return [
            {
                "service": "api",
                "host": "localhost",
                "port": 8000,
                "reachable": True,
                "latency_ms": 1.23,
            }
        ]

    monkeypatch.setattr(docker_client, "list_containers", _fake_containers)
    monkeypatch.setattr(port_probe, "probe_ports", _fake_ports)


# ---------------------------------------------------------------------------
# 엔드포인트 권한/게이트 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_containers_unauthenticated_401(client: AsyncClient, ops_enabled: None) -> None:
    resp = await client.get("/api/v1/admin/ops/containers")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_containers_forbidden_for_admin(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    """핵심: 일반 admin 은 ops 조회 불가 (superadmin 전용)."""
    headers, uid = await _register_and_login(client, "admin@ops.com")
    await _set_role(db_session, uid, "admin")
    resp = await client.get("/api/v1/admin/ops/containers", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_containers_success_for_superadmin(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers, uid = await _register_and_login(client, "super@ops.com")
    await _set_role(db_session, uid, "superadmin")
    resp = await client.get("/api/v1/admin/ops/containers", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["name"] == "clickeye-api"
    assert body[0]["health"] == "healthy"
    # 시크릿/환경변수 필드가 응답에 없어야 함
    assert "env" not in body[0]
    assert "Env" not in body[0]


@pytest.mark.asyncio
async def test_ports_success_for_superadmin(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers, uid = await _register_and_login(client, "super2@ops.com")
    await _set_role(db_session, uid, "superadmin")
    resp = await client.get("/api/v1/admin/ops/ports", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["service"] == "api"
    assert body[0]["reachable"] is True


@pytest.mark.asyncio
async def test_flag_off_returns_404(client: AsyncClient, db_session: AsyncSession) -> None:
    """flag off (기본값) → superadmin 이어도 404 (킬스위치)."""
    headers, uid = await _register_and_login(client, "super3@ops.com")
    await _set_role(db_session, uid, "superadmin")
    resp = await client.get("/api/v1/admin/ops/containers", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 단위 테스트 (DB 불필요)
# ---------------------------------------------------------------------------


def _sensitive_inspect_raw() -> dict[str, Any]:
    """시크릿/명령줄/바인드 경로가 모두 담긴 inspect 원본 (스트립 대상)."""
    return {
        "Id": "deadbeefcafe0001",
        "Name": "/clickeye-api",
        "Path": "uvicorn",
        "Args": ["app.main:app", "--secret-flag", "TOKEN=xyz"],
        "Created": "2026-07-21T00:00:00Z",
        "RestartCount": 2,
        "State": {"Status": "running", "Health": {"Status": "healthy"}},
        "Config": {
            "Image": "clickeye-api:latest",
            "Env": ["JWT_SECRET_KEY=supersecret", "DATABASE_URL=postgres://u:p@h/db"],
            "Cmd": ["uvicorn", "app.main:app"],
            "Entrypoint": ["/entrypoint.sh"],
            "Labels": {"com.secret": "leak"},
            "Healthcheck": {"Test": ["CMD", "curl", "-H", "Authorization: Bearer T"]},
        },
        "HostConfig": {
            "Binds": ["/host/secrets:/app/secrets"],
            "Mounts": [{"Source": "/host/secrets"}],
        },
        "Mounts": [{"Source": "/host/secrets", "Destination": "/app/secrets"}],
        "NetworkSettings": {
            "IPAddress": "172.18.0.5",
            "Ports": {"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]},
        },
    }


@pytest.mark.no_db
def test_normalize_inspect_allowlist_excludes_secrets() -> None:
    """allowlist 정규화: 안전 필드만 반환, 시크릿/명령줄/바인드/네트워크상세 전부 제외."""
    norm = docker_client._normalize_inspect(_sensitive_inspect_raw())
    # 허용 필드
    assert set(norm.keys()) == {
        "id",
        "name",
        "image",
        "state",
        "status",
        "health",
        "created",
        "restart_count",
        "ports",
    }
    assert norm["name"] == "clickeye-api"
    assert norm["image"] == "clickeye-api:latest"
    assert norm["health"] == "healthy"
    assert norm["ports"] == ["8000/tcp->8000"]  # IP 제외
    # 민감 키/값이 결과 어디에도 없어야 함
    forbidden_keys = {
        "Env",
        "Cmd",
        "Args",
        "Path",
        "Entrypoint",
        "Labels",
        "Healthcheck",
        "HostConfig",
        "Binds",
        "Mounts",
        "Config",
        "NetworkSettings",
    }
    assert forbidden_keys.isdisjoint(norm.keys())
    blob = repr(norm)
    assert "supersecret" not in blob
    assert "172.18.0.5" not in blob
    assert "/host/secrets" not in blob


@pytest.mark.no_db
async def test_inspect_container_strips_env_and_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """inspect_container: _get mock 에 Env/Args 가 있어도 결과에서 제거됨."""

    async def _fake_get(path: str) -> dict[str, Any]:
        assert path == "/containers/clickeye-api/json"
        return _sensitive_inspect_raw()

    monkeypatch.setattr(docker_client, "_get", _fake_get)
    result = await docker_client.inspect_container("clickeye-api")
    assert "supersecret" not in repr(result)
    assert result["state"] == "running"
    for forbidden in ("Env", "Args", "Cmd", "Config"):
        assert forbidden not in result


@pytest.mark.no_db
async def test_inspect_container_rejects_bad_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """경로 주입성 식별자는 _get 도달 전 AppError(400) 로 거부."""
    from app.core.exceptions import AppError

    async def _should_not_be_called(path: str) -> dict[str, Any]:
        raise AssertionError("bad id 는 _get 을 호출하면 안 됨")

    monkeypatch.setattr(docker_client, "_get", _should_not_be_called)
    for bad in ("../etc", "a/b/json", "id with space", "id;rm"):
        with pytest.raises(AppError) as exc:
            await docker_client.inspect_container(bad)
        assert exc.value.status_code == 400


@pytest.mark.no_db
def test_parse_health() -> None:
    assert docker_client._parse_health("Up 2 hours (healthy)") == "healthy"
    assert docker_client._parse_health("Up 5 minutes (unhealthy)") == "unhealthy"
    assert docker_client._parse_health("Up 1 second (health: starting)") == "starting"
    assert docker_client._parse_health("Up 3 days") is None


@pytest.mark.no_db
def test_normalize_container_selects_safe_fields() -> None:
    raw = {
        "Id": "deadbeef1234",
        "Names": ["/clickeye-db"],
        "Image": "postgres:16",
        "State": "running",
        "Status": "Up 10 minutes (healthy)",
        "Ports": [{"IP": "0.0.0.0", "PrivatePort": 5432, "PublicPort": 5432, "Type": "tcp"}],
        "Created": 1700000123,
        "Env": ["SHOULD_NOT_APPEAR=1"],
    }
    norm = docker_client._normalize_container(raw)
    assert norm["name"] == "clickeye-db"
    assert norm["ports"] == ["0.0.0.0:5432->5432/tcp"]
    assert norm["health"] == "healthy"
    assert "Env" not in norm
    assert "env" not in norm


@pytest.mark.no_db
def test_parse_port_target() -> None:
    assert port_probe._parse_target("api=localhost:8000") == ("api", "localhost", 8000)
    assert port_probe._parse_target("db:5432") == ("db:5432", "db", 5432)
    assert port_probe._parse_target("bogus") is None
    assert port_probe._parse_target("") is None
    assert port_probe._parse_target("host:notaport") is None
    # 경계값 허용
    assert port_probe._parse_target("edge:0") == ("edge:0", "edge", 0)
    assert port_probe._parse_target("edge:65535") == ("edge:65535", "edge", 65535)
    # 범위 밖(오타/음수) → None (skip)
    assert port_probe._parse_target("bad:99999") is None
    assert port_probe._parse_target("neg:-1") is None


@pytest.mark.no_db
async def test_probe_ports_out_of_range_partial_degrade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """범위 밖 포트 타겟이 섞여도 500 없이, 유효 타겟만 프로브(부분 degrade)."""
    monkeypatch.setattr(
        settings,
        "ops_port_targets",
        ["bad=127.0.0.1:99999", "dead=127.0.0.1:1"],
    )
    results = await port_probe.probe_ports()
    # 범위 밖 타겟은 파싱에서 skip → 결과에 없음. 닫힌 포트는 reachable=False.
    services = {r["service"] for r in results}
    assert "bad" not in services
    assert "dead" in services
    assert next(r for r in results if r["service"] == "dead")["reachable"] is False


@pytest.mark.no_db
async def test_probe_ports_local_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    """실제 로컬 리스닝 소켓에 대한 프로브 (reachable True) + 닫힌 포트 (False)."""
    import asyncio
    import contextlib
    from asyncio import StreamReader, StreamWriter

    async def _handler(reader: StreamReader, writer: StreamWriter) -> None:
        # 서버측 연결을 즉시 닫아 wait_closed() 가 매달리지 않게 한다.
        writer.close()

    server = await asyncio.start_server(_handler, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]

    monkeypatch.setattr(
        settings,
        "ops_port_targets",
        [f"live=127.0.0.1:{port}", "dead=127.0.0.1:1"],
    )
    try:
        results = await port_probe.probe_ports()
    finally:
        server.close()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(server.wait_closed(), timeout=2.0)

    by_service = {r["service"]: r for r in results}
    assert by_service["live"]["reachable"] is True
    assert by_service["live"]["latency_ms"] is not None
    assert by_service["dead"]["reachable"] is False


@pytest.mark.no_db
def test_ops_audit_masks_secrets() -> None:
    assert ops_audit.is_secret_key("JWT_SECRET_KEY") is True
    assert ops_audit.is_secret_key("APP_NAME") is False
    assert ops_audit.mask_value("API_TOKEN", "abcdef") == "***"
    assert ops_audit.mask_value("APP_NAME", "clickeye") == "clickeye"
    # 절단
    long = "x" * 200
    masked = ops_audit.mask_value("APP_NAME", long)
    assert masked is not None
    assert len(masked) <= 100


@pytest.mark.no_db
def test_build_ops_audit_masks_and_truncates() -> None:
    entry = ops_audit.build_ops_audit(
        actor_id=uuid.uuid4(),
        action="ops.env.update",
        resource="managed_env:JWT_SECRET_KEY",
        key="JWT_SECRET_KEY",
        old_value="old-secret",
        new_value="new-secret",
    )
    assert entry.old_value == "***"
    assert entry.new_value == "***"
