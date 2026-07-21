"""CE-305 PR-4 — 화이트리스트 테이블 CRUD 테스트.

핵심 검증:
- 제외 테이블(users 등) 접근 → 404(존재 은닉)
- 화이트리스트 테이블 list/get 마스킹, create/update(editable 만)
- PK/불변 컬럼 변경 거부, delete confirm 필수
- allowed_ops 위반 거부(presets create/delete)
- 권한: admin 403 / superadmin 200 / flag off 404
- 쓰기 감사 기록, 임의 컬럼 주입 거부
"""

from __future__ import annotations

import dataclasses
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.preset import Preset
from app.models.rbac import RoleAuditLog
from app.models.user import User
from app.services.ops import table_registry


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


async def _superadmin(client: AsyncClient, db: AsyncSession, email: str) -> dict[str, str]:
    headers, uid = await _register_and_login(client, email)
    await _set_role(db, uid, "superadmin")
    return headers


@pytest.fixture
def ops_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """feature_ops_panel 활성화."""
    monkeypatch.setattr(settings, "feature_ops_panel", True)


@pytest.fixture
def sensitive_description(monkeypatch: pytest.MonkeyPatch) -> None:
    """app_settings.description 컬럼을 sensitive 로 표시해 마스킹 경로를 검증한다.

    프로덕션 레지스트리엔 민감 컬럼이 없으므로(설정성 데이터) 마스킹 메커니즘 자체를
    엔드포인트 레벨에서 증명하기 위해 테스트에서만 sensitive=True 로 덮어쓴다.
    """
    base = table_registry.REGISTRY["app_settings"]
    new_cols = tuple(
        dataclasses.replace(c, sensitive=True) if c.name == "description" else c
        for c in base.columns
    )
    new_desc = dataclasses.replace(base, columns=new_cols)
    patched = {**table_registry.REGISTRY, "app_settings": new_desc}
    monkeypatch.setattr(table_registry, "REGISTRY", patched)


# ---------------------------------------------------------------------------
# 권한 / 킬스위치
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_forbidden(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers, uid = await _register_and_login(client, "adminonly@opsdb.com")
    await _set_role(db_session, uid, "admin")
    resp = await client.get("/api/v1/admin/ops/tables", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_superadmin_ok(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "ok@opsdb.com")
    resp = await client.get("/api/v1/admin/ops/tables", headers=headers)
    assert resp.status_code == 200
    keys = {t["key"] for t in resp.json()}
    assert {"app_settings", "roi_standards", "presets"} <= keys


@pytest.mark.asyncio
async def test_flag_off_404(client: AsyncClient, db_session: AsyncSession) -> None:
    headers = await _superadmin(client, db_session, "flagoff@opsdb.com")
    resp = await client.get("/api/v1/admin/ops/tables", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 제외 테이블 존재 은닉
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "table",
    ["users", "role_audit_logs", "managed_env_vars", "central_contracts", "licenses"],
)
@pytest.mark.asyncio
async def test_excluded_table_hidden(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None, table: str
) -> None:
    headers = await _superadmin(client, db_session, f"ex-{table}@opsdb.com")
    schema = await client.get(f"/api/v1/admin/ops/tables/{table}/schema", headers=headers)
    assert schema.status_code == 404
    rows = await client.get(f"/api/v1/admin/ops/tables/{table}/rows", headers=headers)
    assert rows.status_code == 404


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_schema_shape(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "schema@opsdb.com")
    resp = await client.get("/api/v1/admin/ops/tables/roi_standards/schema", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pk_column"] == "id"
    by_name = {c["name"]: c for c in body["columns"]}
    assert by_name["category"]["enum"] == [
        "role_rate",
        "solution_effort",
        "complexity_multiplier",
    ]
    # id/created_at 은 편집 불가.
    assert by_name["id"]["editable"] is False
    assert by_name["created_at"]["editable"] is False


# ---------------------------------------------------------------------------
# create / get / list / update / delete (app_settings 전 CRUD)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_get_list(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "crud@opsdb.com")
    create = await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "feature.x", "value": {"enabled": True}, "description": "d"}},
        headers=headers,
    )
    assert create.status_code == 201
    assert create.json()["table"] == "app_settings"
    assert create.json()["pk"] == "feature.x"
    assert create.json()["values"]["key"] == "feature.x"
    assert create.json()["values"]["value"] == {"enabled": True}

    got = await client.get("/api/v1/admin/ops/tables/app_settings/rows/feature.x", headers=headers)
    assert got.status_code == 200
    assert got.json()["values"]["description"] == "d"

    lst = await client.get("/api/v1/admin/ops/tables/app_settings/rows", headers=headers)
    assert lst.status_code == 200
    assert lst.json()["total"] == 1
    assert lst.json()["rows"][0]["key"] == "feature.x"


@pytest.mark.asyncio
async def test_update_editable_only(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "upd@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "k1", "value": 1}},
        headers=headers,
    )
    ok = await client.put(
        "/api/v1/admin/ops/tables/app_settings/rows/k1",
        json={"values": {"value": 2, "description": "updated"}},
        headers=headers,
    )
    assert ok.status_code == 200
    assert ok.json()["values"]["value"] == 2
    assert ok.json()["values"]["description"] == "updated"


@pytest.mark.asyncio
async def test_update_pk_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "pk@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "k2", "value": 1}},
        headers=headers,
    )
    # PK(key) 변경 시도 → 400.
    resp = await client.put(
        "/api/v1/admin/ops/tables/app_settings/rows/k2",
        json={"values": {"key": "renamed"}},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_immutable_column_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "imm@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "k3", "value": 1}},
        headers=headers,
    )
    # updated_at 은 자동/불변 컬럼 → 400.
    resp = await client.put(
        "/api/v1/admin/ops/tables/app_settings/rows/k3",
        json={"values": {"updated_at": "2020-01-01T00:00:00+00:00"}},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_requires_confirm(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "del@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "k4", "value": 1}},
        headers=headers,
    )
    no_confirm = await client.delete(
        "/api/v1/admin/ops/tables/app_settings/rows/k4", headers=headers
    )
    assert no_confirm.status_code == 400

    confirmed = await client.delete(
        "/api/v1/admin/ops/tables/app_settings/rows/k4?confirm=true", headers=headers
    )
    assert confirmed.status_code == 204
    gone = await client.get("/api/v1/admin/ops/tables/app_settings/rows/k4", headers=headers)
    assert gone.status_code == 404


# ---------------------------------------------------------------------------
# 임의 컬럼 주입 / 미허용 create 컬럼
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_arbitrary_column_injection_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "inj@opsdb.com")
    resp = await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "k5", "value": 1, "is_superadmin": True}},
        headers=headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_non_creatable_column_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "nc@opsdb.com")
    # updated_at 은 editable=False & not required → 생성 시 설정 불가.
    resp = await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "k6", "value": 1, "updated_at": "2020-01-01T00:00:00+00:00"}},
        headers=headers,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 검증 (enum / 필수)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_roi_enum_validation(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "roi@opsdb.com")
    bad = await client.post(
        "/api/v1/admin/ops/tables/roi_standards/rows",
        json={"values": {"category": "bogus", "key": "r1", "label": "L", "unit": "KRW"}},
        headers=headers,
    )
    assert bad.status_code == 400

    good = await client.post(
        "/api/v1/admin/ops/tables/roi_standards/rows",
        json={
            "values": {
                "category": "role_rate",
                "key": "r1",
                "label": "L",
                "unit": "KRW",
                "value_numeric": 1000.0,
                "display_order": 1,
                "is_active": True,
            }
        },
        headers=headers,
    )
    assert good.status_code == 201
    assert good.json()["values"]["value_numeric"] == 1000.0


@pytest.mark.asyncio
async def test_required_missing_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "req@opsdb.com")
    resp = await client.post(
        "/api/v1/admin/ops/tables/roi_standards/rows",
        json={"values": {"category": "role_rate", "key": "r2"}},  # label/unit 누락
        headers=headers,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# allowed_ops 위반 (presets: read/update 만)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_presets_create_not_allowed(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "pc@opsdb.com")
    resp = await client.post(
        "/api/v1/admin/ops/tables/presets/rows",
        json={"values": {"name": "N", "slug": "s", "maturity_level": "starter"}},
        headers=headers,
    )
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_presets_update_allowed(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "pu@opsdb.com")
    preset = Preset(name="Old", slug="old-slug", maturity_level="starter")
    db_session.add(preset)
    await db_session.commit()
    await db_session.refresh(preset)

    resp = await client.put(
        f"/api/v1/admin/ops/tables/presets/rows/{preset.id}",
        json={"values": {"name": "New"}},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["values"]["name"] == "New"

    # delete 는 미허용 → 405.
    dele = await client.delete(
        f"/api/v1/admin/ops/tables/presets/rows/{preset.id}?confirm=true", headers=headers
    )
    assert dele.status_code == 405


@pytest.mark.asyncio
async def test_presets_immutable_is_system_rejected(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "pis@opsdb.com")
    preset = Preset(name="Sys", slug="sys-slug", maturity_level="starter")
    db_session.add(preset)
    await db_session.commit()
    await db_session.refresh(preset)

    resp = await client.put(
        f"/api/v1/admin/ops/tables/presets/rows/{preset.id}",
        json={"values": {"is_system": True}},
        headers=headers,
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 마스킹
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sensitive_column_masked(
    client: AsyncClient,
    db_session: AsyncSession,
    ops_enabled: None,
    sensitive_description: None,
) -> None:
    headers = await _superadmin(client, db_session, "mask@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "m1", "value": 1, "description": "topsecret"}},
        headers=headers,
    )
    got = await client.get("/api/v1/admin/ops/tables/app_settings/rows/m1", headers=headers)
    assert got.status_code == 200
    assert got.json()["values"]["description"] == "***"
    assert "topsecret" not in got.text


@pytest.mark.asyncio
async def test_sensitive_column_not_searchable(
    client: AsyncClient,
    db_session: AsyncSession,
    ops_enabled: None,
    sensitive_description: None,
) -> None:
    """W2: sensitive 컬럼(description)은 q 검색 대상에서 제외 → 값 substring 프로빙 불가."""
    headers = await _superadmin(client, db_session, "nosearch@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "s1", "value": 1, "description": "topsecretxyz"}},
        headers=headers,
    )
    # 비민감 컬럼(key)로는 검색됨.
    by_key = await client.get("/api/v1/admin/ops/tables/app_settings/rows?q=s1", headers=headers)
    assert by_key.status_code == 200
    assert by_key.json()["total"] == 1
    # 민감 컬럼 값으로는 검색 불가(마스킹 우회 오라클 차단).
    by_secret = await client.get(
        "/api/v1/admin/ops/tables/app_settings/rows?q=topsecretxyz", headers=headers
    )
    assert by_secret.status_code == 200
    assert by_secret.json()["total"] == 0


@pytest.mark.asyncio
async def test_roi_search_no_error_on_native_enum(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    """W1: roi_standards.category 는 네이티브 PG enum. q 검색이 500 없이 동작해야 한다.

    String 캐스트 덕분에 enum 컬럼도 안전하게 substring 검색된다(SQLite 경로에서 검증;
    실제 PG 경로는 PR-6 pg 마커 테스트로 커버).
    """
    headers = await _superadmin(client, db_session, "roisearch@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/roi_standards/rows",
        json={
            "values": {
                "category": "role_rate",
                "key": "alpha",
                "label": "Alpha Rate",
                "unit": "KRW",
            }
        },
        headers=headers,
    )
    # 문자열 컬럼(key/label) 검색.
    by_key = await client.get(
        "/api/v1/admin/ops/tables/roi_standards/rows?q=alpha", headers=headers
    )
    assert by_key.status_code == 200
    assert by_key.json()["total"] == 1
    # 네이티브 enum(category) 값 검색도 에러 없이 매칭.
    by_enum = await client.get(
        "/api/v1/admin/ops/tables/roi_standards/rows?q=role_rate", headers=headers
    )
    assert by_enum.status_code == 200
    assert by_enum.json()["total"] == 1


# ---------------------------------------------------------------------------
# 감사
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_writes_audit(
    client: AsyncClient, db_session: AsyncSession, ops_enabled: None
) -> None:
    headers = await _superadmin(client, db_session, "audit@opsdb.com")
    await client.post(
        "/api/v1/admin/ops/tables/app_settings/rows",
        json={"values": {"key": "a1", "value": 1}},
        headers=headers,
    )
    logs = (
        (
            await db_session.execute(
                select(RoleAuditLog).where(RoleAuditLog.action == "ops.table.create")
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].resource == "table:app_settings:a1"
