"""프로젝트별 Linear 자격증명 CRUD 테스트.

라우트: PUT/GET/DELETE /api/v1/integrations/projects/{project_id}/linear-credentials
소유권 가드(_require_project_access): 소유자 또는 admin+ 만 접근 — IDOR 차단(리뷰 HIGH 반영).
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

BASE = "/api/v1/integrations/projects"
API_KEY = "lin_api_secret_plaintext_1234567890"
TEAM_ID = "team-uuid-abcd-1234"


def _url(project_id: str) -> str:
    return f"{BASE}/{project_id}/linear-credentials"


async def _register_login(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234!", "display_name": "테스터"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "pass1234!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture
async def owner_ctx(client: AsyncClient) -> tuple[dict[str, str], str]:
    """소유자 인증 헤더 + 그 사용자가 소유한 프로젝트 id."""
    headers = await _register_login(client, "plc_owner@test.com")
    resp = await client.post(
        "/api/v1/projects/",
        json={"name": "PLC 테스트 프로젝트"},
        headers=headers,
    )
    assert resp.status_code in (200, 201), resp.text
    return headers, resp.json()["id"]


@pytest.mark.asyncio
async def test_put_registers_credentials_and_masks_key(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """소유 프로젝트 PUT 등록 → 200, 응답은 마스킹 키·팀 ID, 평문 키 무노출."""
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["team_id"] == TEAM_ID
    assert body["updated_at"]
    # 평문 키는 절대 반환되지 않는다
    assert API_KEY not in resp.text
    assert "****" in body["api_key_masked"]


@pytest.mark.asyncio
async def test_get_returns_masked_credentials(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """등록 후 GET → 마스킹 키·팀 ID 반환, 평문 무노출."""
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    resp = await client.get(_url(project_id), headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["team_id"] == TEAM_ID
    assert "****" in body["api_key_masked"]
    assert API_KEY not in resp.text


@pytest.mark.asyncio
async def test_get_missing_returns_404(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """소유 프로젝트라도 자격증명 미등록이면 GET → 404."""
    headers, project_id = owner_ctx
    resp = await client.get(_url(project_id), headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_removes_credentials(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """DELETE → 204, 이후 GET 404."""
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    resp = await client.delete(_url(project_id), headers=headers)
    assert resp.status_code == 204
    follow = await client.get(_url(project_id), headers=headers)
    assert follow.status_code == 404


@pytest.mark.asyncio
async def test_non_owner_cannot_touch_credentials(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """IDOR 차단 — 타 사용자는 소유자 프로젝트 자격증명에 PUT/GET/DELETE 전부 404."""
    owner_headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=owner_headers,
    )
    intruder = await _register_login(client, "plc_intruder@test.com")
    put_resp = await client.put(
        _url(project_id),
        json={"api_key": "lin_api_evil_overwrite_0000000000", "team_id": "evil-team"},
        headers=intruder,
    )
    assert put_resp.status_code == 404
    get_resp = await client.get(_url(project_id), headers=intruder)
    assert get_resp.status_code == 404
    del_resp = await client.delete(_url(project_id), headers=intruder)
    assert del_resp.status_code == 404
    # 소유자 데이터는 훼손되지 않았다
    intact = await client.get(_url(project_id), headers=owner_headers)
    assert intact.status_code == 200
    assert intact.json()["team_id"] == TEAM_ID


@pytest.mark.asyncio
async def test_unknown_project_returns_404(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str]
) -> None:
    """존재하지 않는 프로젝트 id → 404 (소유권 가드가 존재 여부를 숨김)."""
    headers, _ = owner_ctx
    resp = await client.put(
        _url(str(uuid4())),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_requires_auth(client: AsyncClient) -> None:
    """인증 헤더 없이 PUT → 401."""
    resp = await client.put(
        _url(str(uuid4())),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
    )
    assert resp.status_code == 401


# ── 프로젝트별 webhook (signing secret + 자동 등록) ──

WEBHOOK_SECRET = "lin_wh_project_secret_0987654321"
TUNNEL_URL = "https://proj-a.example.dev"


@pytest.mark.asyncio
async def test_put_stores_webhook_secret_without_echoing_it(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """webhook_secret 저장 → 응답은 설정 여부(bool)만 노출, 평문 무반환."""
    from app.services import linear_service

    monkeypatch.setattr(linear_service, "ensure_webhook", lambda *a, **k: "wh_id_1")
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["webhook_secret_set"] is True
    assert WEBHOOK_SECRET not in resp.text
    # GET 도 동일 형상
    got = await client.get(_url(project_id), headers=headers)
    assert got.json()["webhook_secret_set"] is True
    assert WEBHOOK_SECRET not in got.text


@pytest.mark.asyncio
async def test_put_registers_webhook_with_project_key(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """tunnel + secret 이 있으면 프로젝트 자격증명으로 webhook 등록, 반환 ID 저장."""
    from app.services import linear_service

    calls: list[tuple] = []

    def _fake_ensure(api_key, team_id, url, secret=None, label="ClickEye"):  # type: ignore[no-untyped-def]
        calls.append((api_key, team_id, url, secret, label))
        return "wh_id_registered"

    monkeypatch.setattr(linear_service, "ensure_webhook", _fake_ensure)
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["linear_webhook_id"] == "wh_id_registered"
    assert len(calls) == 1
    api_key, team_id, url, secret, label = calls[0]
    assert api_key == API_KEY  # 전역 키가 아니라 프로젝트 평문 키로 등록
    assert team_id == TEAM_ID
    assert url == f"{TUNNEL_URL}/webhook/linear"
    assert secret == WEBHOOK_SECRET
    # 프로젝트별 고유 label — 같은 워크스페이스를 공유하는 다른 프로젝트/전역 훅을 덮어쓰지 않는다
    assert label == f"ClickEye:{project_id}"


@pytest.mark.asyncio
async def test_put_skips_registration_without_tunnel(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """tunnel 이 해석되지 않으면 등록을 시도하지 않고 저장만 한다."""
    from app.services import linear_service

    def _must_not_call(*a, **k):  # type: ignore[no-untyped-def]
        raise AssertionError("tunnel 없이 webhook 등록을 시도했다")

    monkeypatch.setattr(linear_service, "ensure_webhook", _must_not_call)
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID, "webhook_secret": WEBHOOK_SECRET},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["webhook_secret_set"] is True
    assert resp.json()["linear_webhook_id"] is None


@pytest.mark.asyncio
async def test_put_falls_back_to_user_tunnel_url(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """요청에 tunnel_url 이 없으면 요청 사용자의 전역 tunnel_url 로 폴백."""
    from app.services import linear_service

    calls: list[str] = []
    monkeypatch.setattr(
        linear_service,
        "ensure_webhook",
        lambda api_key, team_id, url, secret=None, label="ClickEye": (
            calls.append(url) or "wh_id_fallback"  # type: ignore[func-returns-value]
        ),
    )
    headers, project_id = owner_ctx
    # 전역(사용자) Linear 설정에 tunnel_url 등록 — 전역 webhook 등록은 tunnel 유무로만 동작
    saved = await client.post(
        "/api/v1/me/linear-credentials/",
        json={
            "api_key": "lin_api_user_global_key_00000",
            "team_id": "user-team",
            "tunnel_url": "https://user-global.example.dev",
        },
        headers=headers,
    )
    assert saved.status_code == 200, saved.text
    calls.clear()  # 전역 저장이 유발한 호출은 이 테스트의 관심사가 아니다

    resp = await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID, "webhook_secret": WEBHOOK_SECRET},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert calls == ["https://user-global.example.dev/webhook/linear"]
    assert resp.json()["linear_webhook_id"] == "wh_id_fallback"


@pytest.mark.asyncio
async def test_webhook_registration_failure_keeps_credentials(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """등록 실패는 저장을 막지 않는다(전역 플로우와 동일) — 200 + webhook ID 없음."""
    from app.services import linear_service

    def _boom(*a, **k):  # type: ignore[no-untyped-def]
        raise RuntimeError("Linear API 5xx")

    monkeypatch.setattr(linear_service, "ensure_webhook", _boom)
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["linear_webhook_id"] is None
    follow = await client.get(_url(project_id), headers=headers)
    assert follow.status_code == 200
    assert follow.json()["webhook_secret_set"] is True


@pytest.mark.asyncio
async def test_put_without_webhook_fields_regression(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """webhook 필드 없는 기존 요청 형상 → webhook_secret_set=False, 등록 시도 없음."""
    from app.services import linear_service

    def _must_not_call(*a, **k):  # type: ignore[no-untyped-def]
        raise AssertionError("secret 없이 webhook 등록을 시도했다")

    monkeypatch.setattr(linear_service, "ensure_webhook", _must_not_call)
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["webhook_secret_set"] is False
    assert body["linear_webhook_id"] is None


@pytest.mark.asyncio
async def test_second_save_without_secret_keeps_stored_secret(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """부분 갱신 — 시크릿을 뺀 두 번째 저장(team_id 만 수정)이 저장된 시크릿을 지우지 않는다.

    프론트는 저장 후 입력을 비워 null 로 보낸다. 무조건 대입하면 여기서 시크릿이 소실돼
    수신부가 이 프로젝트의 서명을 검증할 수 없게 된다.
    """
    from app.services import linear_service

    secrets_seen: list[str | None] = []

    def _fake_ensure(api_key, team_id, url, secret=None, label="ClickEye"):  # type: ignore[no-untyped-def]
        secrets_seen.append(secret)
        return "wh_id_1"

    monkeypatch.setattr(linear_service, "ensure_webhook", _fake_ensure)
    headers, project_id = owner_ctx
    first = await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    assert first.json()["webhook_secret_set"] is True

    second = await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": "team-uuid-changed",
            "webhook_secret": None,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    assert second.status_code == 200, second.text
    assert second.json()["webhook_secret_set"] is True
    assert second.json()["team_id"] == "team-uuid-changed"
    # 저장된 시크릿으로 훅을 다시 맞춰 새 team_id 와 어긋나지 않게 한다
    assert secrets_seen == [WEBHOOK_SECRET, WEBHOOK_SECRET]

    follow = await client.get(_url(project_id), headers=headers)
    assert follow.json()["webhook_secret_set"] is True


@pytest.mark.asyncio
async def test_empty_string_secret_is_not_a_deletion(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """빈 문자열도 '변경 없음' — 명시적 삭제 의미를 두지 않는다(전역 라우트 의미론)."""
    from app.services import linear_service

    monkeypatch.setattr(linear_service, "ensure_webhook", lambda *a, **k: "wh_id_1")
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    resp = await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID, "webhook_secret": ""},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["webhook_secret_set"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_url",
    [
        "http://evil.example.com",
        "not-a-url",
        "https://",
        "javascript:alert(1)",
        "ftp://host/path",
    ],
)
async def test_put_rejects_non_https_tunnel_url(
    client: AsyncClient,
    owner_ctx: tuple[dict[str, str], str],
    monkeypatch: pytest.MonkeyPatch,
    bad_url: str,
) -> None:
    """tunnel_url 은 호스트를 가진 https 만 — 임의 URL 로 훅을 재지향할 수 없다."""
    from app.services import linear_service

    def _must_not_call(*a, **k):  # type: ignore[no-untyped-def]
        raise AssertionError("검증 실패한 tunnel_url 로 webhook 등록을 시도했다")

    monkeypatch.setattr(linear_service, "ensure_webhook", _must_not_call)
    headers, project_id = owner_ctx
    resp = await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": bad_url,
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_delete_unregisters_remote_webhook(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """DELETE 는 Linear 원격 훅도 해지한다 — 행만 지우면 훅이 계속 전송된다."""
    from app.services import linear_service

    monkeypatch.setattr(linear_service, "ensure_webhook", lambda *a, **k: "wh_id_to_delete")
    deleted: list[tuple[str, str]] = []
    monkeypatch.setattr(
        linear_service,
        "delete_webhook",
        lambda api_key, webhook_id: (  # type: ignore[misc]
            deleted.append((api_key, webhook_id)) or True
        ),
    )
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    resp = await client.delete(_url(project_id), headers=headers)
    assert resp.status_code == 204
    assert deleted == [(API_KEY, "wh_id_to_delete")]


@pytest.mark.asyncio
async def test_delete_proceeds_when_unregister_fails(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """원격 해지 실패는 로깅 후 무시 — 자격증명 삭제 자체는 계속 진행한다."""
    from app.services import linear_service

    def _boom(*a, **k):  # type: ignore[no-untyped-def]
        raise RuntimeError("Linear API 5xx")

    monkeypatch.setattr(linear_service, "ensure_webhook", lambda *a, **k: "wh_id_1")
    monkeypatch.setattr(linear_service, "delete_webhook", _boom)
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={
            "api_key": API_KEY,
            "team_id": TEAM_ID,
            "webhook_secret": WEBHOOK_SECRET,
            "tunnel_url": TUNNEL_URL,
        },
        headers=headers,
    )
    resp = await client.delete(_url(project_id), headers=headers)
    assert resp.status_code == 204
    assert (await client.get(_url(project_id), headers=headers)).status_code == 404


@pytest.mark.asyncio
async def test_delete_without_webhook_skips_unregister(
    client: AsyncClient, owner_ctx: tuple[dict[str, str], str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """훅이 등록된 적 없으면 해지를 시도하지 않는다 — 회귀 0."""
    from app.services import linear_service

    def _must_not_call(*a, **k):  # type: ignore[no-untyped-def]
        raise AssertionError("등록된 적 없는 훅의 해지를 시도했다")

    monkeypatch.setattr(linear_service, "delete_webhook", _must_not_call)
    headers, project_id = owner_ctx
    await client.put(
        _url(project_id),
        json={"api_key": API_KEY, "team_id": TEAM_ID},
        headers=headers,
    )
    assert (await client.delete(_url(project_id), headers=headers)).status_code == 204
