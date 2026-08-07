"""CE-421 — webhook.env WEBHOOK_SECRET_MAP 렌더 테스트.

렌더는 MAP 라인만 소유하며(타 라인 보존), 수신부 파서를 깨는 값은 fail-closed 로 제외한다.
"""

from __future__ import annotations

import os
import stat
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.project import Project
from app.models.project_linear_credentials import ProjectLinearCredentials
from app.models.rbac import RoleAuditLog
from app.models.user import User
from app.services.ops import docker_client

_STATUS_URL = "/api/v1/admin/ops/env/webhook/status"
_RENDER_URL = "/api/v1/admin/ops/env/webhook/render"


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
def webhook_env_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """feature_ops_panel 활성화 + webhook_env_path 를 tmp 로 지정."""
    monkeypatch.setattr(settings, "feature_ops_panel", True)
    env_file = tmp_path / "managed" / "webhook.env"
    monkeypatch.setattr(settings, "webhook_env_path", str(env_file))
    return env_file


async def _add_credential(
    db: AsyncSession, owner_email: str, project_name: str, team_id: str, secret: str | None
) -> uuid.UUID:
    """프로젝트 + Linear 자격증명 1건 생성. project_id 반환."""
    owner = User(
        email=owner_email,
        password_hash="x",
        display_name="owner",
    )
    db.add(owner)
    await db.flush()
    project = Project(
        owner_id=owner.id,
        name=project_name,
        slug=project_name.lower().replace(" ", "-"),
    )
    db.add(project)
    await db.flush()
    db.add(
        ProjectLinearCredentials(
            project_id=project.id,
            encrypted_api_key="enc",
            team_id=team_id,
            webhook_secret=secret,
        )
    )
    await db.commit()
    return uuid.UUID(str(project.id))


# ---------------------------------------------------------------------------
# 렌더 — MAP 라인 교체 + 타 라인 보존
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_replaces_map_line_and_preserves_others(
    client: AsyncClient,
    db_session: AsyncSession,
    webhook_env_enabled: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = await _superadmin(client, db_session, "wh-render@ops.com")
    await _add_credential(db_session, "o1@ops.com", "Beta", "team-b", "lin_wh_b")
    await _add_credential(db_session, "o2@ops.com", "Alpha", "team-a", "lin_wh_a")

    # 운영자가 수기로 관리해 온 파일 — 주석/레거시 라인/기존 MAP 값.
    webhook_env_enabled.parent.mkdir(parents=True, exist_ok=True)
    webhook_env_enabled.write_text(
        "# 운영자 수기 주석\nWEBHOOK_SECRET=legacy_single\nWEBHOOK_SECRETS=\n"
        "WEBHOOK_SECRET_MAP=stale-team=stale_secret\n# 꼬리 주석\n",
        encoding="utf-8",
    )

    # docker 를 건드리면 즉시 실패 — 렌더 경로는 docker 미의존.
    async def _boom(*args: object, **kwargs: object) -> object:
        raise AssertionError("webhook 렌더는 docker 를 호출하면 안 됨")

    monkeypatch.setattr(docker_client, "list_containers", _boom)
    monkeypatch.setattr(docker_client, "inspect_container", _boom)
    monkeypatch.setattr(docker_client, "_get", _boom)

    resp = await client.post(_RENDER_URL, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["entry_count"] == 2
    assert body["skipped"] == []
    assert body["legacy_present"] is True
    assert "--force-recreate" in body["restart_command"]
    assert "webhook" in body["restart_command"]
    # 응답에 시크릿 평문이 없어야 한다.
    assert "lin_wh_a" not in resp.text

    content = webhook_env_enabled.read_text(encoding="utf-8")
    # MAP 은 team_id 정렬로 결정적. 기존 stale 값은 사라진다.
    assert "WEBHOOK_SECRET_MAP=team-a=lin_wh_a,team-b=lin_wh_b\n" in content
    assert "stale_secret" not in content
    # 타 라인은 원문 그대로 보존.
    assert "# 운영자 수기 주석" in content
    assert "WEBHOOK_SECRET=legacy_single" in content
    assert "WEBHOOK_SECRETS=" in content
    assert "# 꼬리 주석" in content
    # 시크릿 파일이므로 소유자 전용.
    assert stat.S_IMODE(os.stat(webhook_env_enabled).st_mode) == 0o600


@pytest.mark.asyncio
async def test_render_creates_file_when_missing(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "wh-new@ops.com")
    await _add_credential(db_session, "o3@ops.com", "Gamma", "team-g", "lin_wh_g")
    assert not webhook_env_enabled.exists()

    resp = await client.post(_RENDER_URL, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["entry_count"] == 1
    assert resp.json()["legacy_present"] is False

    content = webhook_env_enabled.read_text(encoding="utf-8")
    assert content.startswith("# ClickEye webhook")
    assert "WEBHOOK_SECRET_MAP=team-g=lin_wh_g\n" in content
    assert stat.S_IMODE(os.stat(webhook_env_enabled).st_mode) == 0o600


@pytest.mark.asyncio
async def test_render_keeps_rotation_pair_for_same_team(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    """같은 팀에 시크릿이 둘이면(로테이션) 둘 다 남긴다 — 수신부가 허용하는 의미론."""
    headers = await _superadmin(client, db_session, "wh-rot@ops.com")
    await _add_credential(db_session, "o4@ops.com", "Rot A", "team-r", "lin_wh_old")
    await _add_credential(db_session, "o5@ops.com", "Rot B", "team-r", "lin_wh_new")

    resp = await client.post(_RENDER_URL, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["entry_count"] == 2
    content = webhook_env_enabled.read_text(encoding="utf-8")
    assert "WEBHOOK_SECRET_MAP=team-r=lin_wh_new,team-r=lin_wh_old\n" in content


# ---------------------------------------------------------------------------
# fail-closed — 파서 파괴 문자 제외
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_skips_parser_breaking_values(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "wh-skip@ops.com")
    await _add_credential(db_session, "o6@ops.com", "Good", "team-ok", "lin_wh_ok")
    await _add_credential(db_session, "o7@ops.com", "Comma", "team-c", "lin,wh,comma")
    await _add_credential(db_session, "o8@ops.com", "Newline", "team-n", "lin\nwh")
    await _add_credential(db_session, "o9@ops.com", "Space", "team-s", " lin_wh_pad ")
    await _add_credential(db_session, "o10@ops.com", "EqTeam", "team=eq", "lin_wh_eq")

    resp = await client.post(_RENDER_URL, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["entry_count"] == 1
    skipped_names = sorted(item["project_name"] for item in body["skipped"])
    assert skipped_names == ["Comma", "EqTeam", "Newline", "Space"]
    # 사유는 남기되 시크릿 값은 노출하지 않는다.
    assert all(item["reason"] for item in body["skipped"])
    assert "lin_wh_eq" not in resp.text
    assert "lin,wh,comma" not in resp.text

    content = webhook_env_enabled.read_text(encoding="utf-8")
    assert "WEBHOOK_SECRET_MAP=team-ok=lin_wh_ok\n" in content
    assert "team-c" not in content
    assert "team=eq" not in content


@pytest.mark.asyncio
async def test_render_ignores_projects_without_secret(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "wh-nosec@ops.com")
    await _add_credential(db_session, "o11@ops.com", "NoSecret", "team-x", None)

    resp = await client.post(_RENDER_URL, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    # 미등록은 제외 사유가 아니라 그냥 대상 아님.
    assert body["entry_count"] == 0
    assert body["skipped"] == []
    assert "WEBHOOK_SECRET_MAP=\n" in webhook_env_enabled.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_reports_file_and_projects(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    headers = await _superadmin(client, db_session, "wh-status@ops.com")
    await _add_credential(db_session, "o12@ops.com", "WithSecret", "team-w", "lin_wh_w")
    await _add_credential(db_session, "o13@ops.com", "NoSecret", "team-z", None)

    # 파일 없음 상태.
    resp = await client.get(_STATUS_URL, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["file_exists"] is False
    assert body["map_line_present"] is False
    assert body["legacy_present"] is False
    by_name = {p["project_name"]: p for p in body["projects"]}
    assert by_name["WithSecret"]["has_secret"] is True
    assert by_name["WithSecret"]["team_id"] == "team-w"
    assert by_name["NoSecret"]["has_secret"] is False
    assert "lin_wh_w" not in resp.text

    # 렌더 후 상태.
    await client.post(_RENDER_URL, headers=headers)
    resp2 = await client.get(_STATUS_URL, headers=headers)
    body2 = resp2.json()
    assert body2["file_exists"] is True
    assert body2["map_line_present"] is True
    assert body2["legacy_present"] is False


@pytest.mark.asyncio
async def test_status_legacy_present_only_for_filled_value(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    """빈 WEBHOOK_SECRET= 은 example 기본형이라 경고 대상이 아니다."""
    headers = await _superadmin(client, db_session, "wh-legacy@ops.com")
    webhook_env_enabled.parent.mkdir(parents=True, exist_ok=True)
    webhook_env_enabled.write_text("WEBHOOK_SECRET=\nWEBHOOK_SECRETS=\n", encoding="utf-8")
    resp = await client.get(_STATUS_URL, headers=headers)
    assert resp.json()["legacy_present"] is False

    webhook_env_enabled.write_text("WEBHOOK_SECRETS=a,b\n", encoding="utf-8")
    resp2 = await client.get(_STATUS_URL, headers=headers)
    assert resp2.json()["legacy_present"] is True

    # 주석 처리된 레거시 라인은 무효.
    webhook_env_enabled.write_text("# WEBHOOK_SECRET=commented\n", encoding="utf-8")
    resp3 = await client.get(_STATUS_URL, headers=headers)
    assert resp3.json()["legacy_present"] is False


# ---------------------------------------------------------------------------
# 감사 / 권한 / 킬스위치
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_writes_audit_without_secret(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    from sqlalchemy import select

    headers = await _superadmin(client, db_session, "wh-audit@ops.com")
    await _add_credential(db_session, "o14@ops.com", "Audited", "team-au", "lin_wh_audit")
    await client.post(_RENDER_URL, headers=headers)

    logs = (
        (
            await db_session.execute(
                select(RoleAuditLog).where(RoleAuditLog.action == "ops.env.webhook_render")
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert "lin_wh_audit" not in (logs[0].new_value or "")
    assert "1 entries" in (logs[0].new_value or "")


@pytest.mark.asyncio
async def test_admin_forbidden(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    headers, uid = await _register_and_login(client, "wh-adminonly@ops.com")
    await _set_role(db_session, uid, "admin")
    assert (await client.get(_STATUS_URL, headers=headers)).status_code == 403
    assert (await client.post(_RENDER_URL, headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_anonymous_rejected(
    client: AsyncClient, db_session: AsyncSession, webhook_env_enabled: Path
) -> None:
    assert (await client.get(_STATUS_URL)).status_code in (401, 403)
    assert (await client.post(_RENDER_URL)).status_code in (401, 403)


@pytest.mark.asyncio
async def test_flag_off_404(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "feature_ops_panel", False)
    headers = await _superadmin(client, db_session, "wh-flagoff@ops.com")
    assert (await client.get(_STATUS_URL, headers=headers)).status_code == 404
    assert (await client.post(_RENDER_URL, headers=headers)).status_code == 404
