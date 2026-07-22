"""CE-305 PR-3 — 관리형 env CRUD + 수동 적용(렌더/명령) 테스트."""

from __future__ import annotations

import os
import stat
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import crypto
from app.models.managed_env_var import ManagedEnvVar
from app.models.rbac import RoleAuditLog
from app.models.user import User
from app.services.ops import docker_client, ops_audit


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
def ops_env_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """feature_ops_panel 활성화 + managed_env_path 를 tmp 로 지정."""
    monkeypatch.setattr(settings, "feature_ops_panel", True)
    env_file = tmp_path / "api.env"
    monkeypatch.setattr(settings, "managed_env_path", str(env_file))
    monkeypatch.setattr(settings, "ops_managed_services", ["api"])
    return env_file


async def _superadmin(client: AsyncClient, db: AsyncSession, email: str) -> dict[str, str]:
    headers, uid = await _register_and_login(client, email)
    await _set_role(db, uid, "superadmin")
    return headers


# ---------------------------------------------------------------------------
# 편집 제외 키
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"])
@pytest.mark.asyncio
async def test_excluded_key_put_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path, key: str
) -> None:
    headers = await _superadmin(client, db_session, f"s-{key.lower()}@ops.com")
    resp = await client.put(f"/api/v1/admin/ops/env/{key}", json={"value": "x"}, headers=headers)
    assert resp.status_code == 400


@pytest.mark.parametrize("key", ["JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"])
@pytest.mark.asyncio
async def test_excluded_key_delete_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path, key: str
) -> None:
    headers = await _superadmin(client, db_session, f"d-{key.lower()}@ops.com")
    resp = await client.delete(f"/api/v1/admin/ops/env/{key}", headers=headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unknown_key_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "unknown@ops.com")
    resp = await client.put(
        "/api/v1/admin/ops/env/TOTALLY_UNKNOWN", json={"value": "x"}, headers=headers
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# upsert + 암호화 + 조회 마스킹
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_stores_encrypted(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "enc@ops.com")
    value = '["http://localhost:3000"]'
    resp = await client.put(
        "/api/v1/admin/ops/env/CORS_ORIGINS", json={"value": value}, headers=headers
    )
    assert resp.status_code == 204

    row = (
        await db_session.execute(select(ManagedEnvVar).where(ManagedEnvVar.key == "CORS_ORIGINS"))
    ).scalar_one()
    # DB 저장값은 평문이 아니어야 하며, 복호 시 원문 일치.
    assert row.value_encrypted != value
    assert crypto.decrypt(str(row.value_encrypted)) == value


@pytest.mark.asyncio
async def test_get_masks_secret_and_shows_plain(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "mask@ops.com")
    await client.put(
        "/api/v1/admin/ops/env/ANTHROPIC_API_KEY",
        json={"value": "sk-ant-supersecret"},
        headers=headers,
    )
    await client.put("/api/v1/admin/ops/env/LOG_LEVEL", json={"value": "info"}, headers=headers)
    resp = await client.get("/api/v1/admin/ops/env", headers=headers)
    assert resp.status_code == 200
    by_key = {item["key"]: item for item in resp.json()}

    secret = by_key["ANTHROPIC_API_KEY"]
    assert secret["is_secret"] is True
    assert secret["has_value"] is True
    assert secret["masked_value"] == "***"
    # 평문 시크릿이 응답 어디에도 없어야 함.
    assert "sk-ant-supersecret" not in resp.text

    plain = by_key["LOG_LEVEL"]
    assert plain["is_secret"] is False
    assert plain["masked_value"] == "info"

    # 제외 키는 목록에 보이되 editable=False.
    excluded = by_key["JWT_SECRET_KEY"]
    assert excluded["editable"] is False


@pytest.mark.asyncio
async def test_delete_removes_key(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "del@ops.com")
    await client.put("/api/v1/admin/ops/env/LOG_LEVEL", json={"value": "debug"}, headers=headers)
    resp = await client.delete("/api/v1/admin/ops/env/LOG_LEVEL", headers=headers)
    assert resp.status_code == 204
    row = (
        await db_session.execute(select(ManagedEnvVar).where(ManagedEnvVar.key == "LOG_LEVEL"))
    ).scalar_one_or_none()
    assert row is None


# ---------------------------------------------------------------------------
# 렌더 + pending + docker 미실행
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_writes_file_and_returns_command_without_docker(
    client: AsyncClient,
    db_session: AsyncSession,
    ops_env_enabled: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = await _superadmin(client, db_session, "render@ops.com")
    await client.put("/api/v1/admin/ops/env/LOG_LEVEL", json={"value": "warning"}, headers=headers)

    # docker 가 호출되면 즉시 실패하도록 스텁 — 렌더 경로는 docker 를 건드리지 않음을 단언.
    async def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("render 는 docker 를 호출하면 안 됨")

    monkeypatch.setattr(docker_client, "list_containers", _boom)
    monkeypatch.setattr(docker_client, "inspect_container", _boom)
    monkeypatch.setattr(docker_client, "_get", _boom)

    resp = await client.post(
        "/api/v1/admin/ops/env/render", json={"confirm": True}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["applied_count"] == 1
    assert "--force-recreate" in body["recreate_command"]
    assert body["services"] == ["api"]
    assert body["pending"] == []

    # 파일이 실제로 렌더되고 KEY=VALUE 를 포함.
    content = ops_env_enabled.read_text(encoding="utf-8")
    assert "LOG_LEVEL=warning" in content


@pytest.mark.asyncio
async def test_render_requires_confirm(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "confirm@ops.com")
    resp = await client.post(
        "/api/v1/admin/ops/env/render", json={"confirm": False}, headers=headers
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_pending_transitions(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "pending@ops.com")
    await client.put("/api/v1/admin/ops/env/LOG_LEVEL", json={"value": "info"}, headers=headers)
    # 렌더 전: pending=true
    resp = await client.get("/api/v1/admin/ops/env", headers=headers)
    by_key = {i["key"]: i for i in resp.json()}
    assert by_key["LOG_LEVEL"]["pending"] is True

    # 렌더 후: pending=false
    await client.post("/api/v1/admin/ops/env/render", json={"confirm": True}, headers=headers)
    resp2 = await client.get("/api/v1/admin/ops/env", headers=headers)
    by_key2 = {i["key"]: i for i in resp2.json()}
    assert by_key2["LOG_LEVEL"]["pending"] is False


# ---------------------------------------------------------------------------
# 권한 / 킬스위치
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_forbidden(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers, uid = await _register_and_login(client, "adminonly@ops.com")
    await _set_role(db_session, uid, "admin")
    resp = await client.get("/api/v1/admin/ops/env", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_superadmin_ok(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "ok@ops.com")
    resp = await client.get("/api/v1/admin/ops/env", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_flag_off_404(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ambient env(.env 의 FEATURE_OPS_PANEL) 오염 방지 — 플래그 off 를 명시적으로 강제.
    monkeypatch.setattr(settings, "feature_ops_panel", False)
    headers = await _superadmin(client, db_session, "flagoff@ops.com")
    resp = await client.get("/api/v1/admin/ops/env", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 감사
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_writes_masked_audit(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "audit@ops.com")
    await client.put(
        "/api/v1/admin/ops/env/ANTHROPIC_API_KEY",
        json={"value": "sk-ant-should-be-masked"},
        headers=headers,
    )
    logs = (
        (
            await db_session.execute(
                select(RoleAuditLog).where(RoleAuditLog.action == "ops.env.upsert")
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    # 시크릿 키의 값은 마스킹되어 감사에 평문이 남지 않음.
    assert logs[0].new_value == "***"
    assert "sk-ant-should-be-masked" not in (logs[0].new_value or "")


# ---------------------------------------------------------------------------
# W2 — 감사 마스킹 SSOT (키명 힌트와 무관하게 권위 플래그로 마스킹)
# ---------------------------------------------------------------------------


@pytest.mark.no_db
def test_build_ops_audit_masks_hintless_secret_via_flag() -> None:
    """힌트 substring 없는 키라도 is_secret=True 면 마스킹(평문 미기록)."""
    # 'PLAIN_NAME' 은 secret/token/key/password/credential 힌트가 없음.
    entry = ops_audit.build_ops_audit(
        actor_id=uuid.uuid4(),
        action="ops.env.upsert",
        resource="managed_env:PLAIN_NAME",
        key="PLAIN_NAME",
        old_value=None,
        new_value="topsecretvalue",
        is_secret=True,
    )
    assert entry.new_value == "***"

    # is_secret=None 이면 기존 키명 휴리스틱 fallback — 힌트 없는 키는 평문 유지(비시크릿).
    entry_fallback = ops_audit.build_ops_audit(
        actor_id=uuid.uuid4(),
        action="ops.env.upsert",
        resource="managed_env:PLAIN_NAME",
        key="PLAIN_NAME",
        old_value=None,
        new_value="visible",
    )
    assert entry_fallback.new_value == "visible"


@pytest.mark.no_db
def test_mask_value_flag_overrides_heuristic() -> None:
    # 힌트 있는 키라도 is_secret=False 면 비마스킹(플래그 우선).
    assert ops_audit.mask_value("API_TOKEN", "abc", is_secret=False) == "abc"
    # 힌트 없는 키라도 is_secret=True 면 마스킹.
    assert ops_audit.mask_value("PLAIN", "abc", is_secret=True) == "***"


# ---------------------------------------------------------------------------
# W1 — 렌더 파일 권한 0o600 강제(기존 파일이어도)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_forces_0600_even_on_existing_file(
    client: AsyncClient, db_session: AsyncSession, ops_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "perm@ops.com")
    await client.put(
        "/api/v1/admin/ops/env/OPENAI_API_KEY",
        json={"value": "sk-secret"},
        headers=headers,
    )
    # 느슨한 권한(group/other 읽기)으로 파일을 미리 생성해 둔다.
    ops_env_enabled.write_text("STALE=1\n", encoding="utf-8")
    os.chmod(ops_env_enabled, 0o644)

    resp = await client.post(
        "/api/v1/admin/ops/env/render", json={"confirm": True}, headers=headers
    )
    assert resp.status_code == 200

    # 렌더 후 파일 권한이 0o600 으로 강제되어 group/other 읽기 불가.
    mode = stat.S_IMODE(os.stat(ops_env_enabled).st_mode)
    assert mode == 0o600
    # 스냅샷 파일도 0o600.
    state_file = Path(str(ops_env_enabled) + ".state.json")
    assert stat.S_IMODE(os.stat(state_file).st_mode) == 0o600
