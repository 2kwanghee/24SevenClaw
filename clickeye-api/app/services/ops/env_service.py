"""관리형 환경변수 서비스 (CE-305 PR-3, superadmin 전용).

정책 요약:
- **편집 제외(하드)**: JWT_SECRET_KEY(crypto Fernet 파생 → 변경 시 기존 암호값 전부
  복호 불가), DATABASE_URL, REDIS_URL. 조회 목록엔 보이되 편집/삭제는 400 으로 거부.
- **편집 가능**: 앱 레벨 설정 위주의 allowlist(ALLOWED_KEYS). allowlist 밖 키는 upsert 400.
- 값은 app.core.crypto(Fernet)로 at-rest 암호화 저장. 시크릿 키는 조회 시 값 미반환.
- **적용은 수동**: render_to_file() 이 파일만 렌더하고, 재생성 명령 문자열을 반환할 뿐
  docker/재생성을 절대 실행하지 않는다(이 모듈은 docker 를 import 하지도 호출하지도 않음).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import crypto
from app.core.exceptions import AppError
from app.models.managed_env_var import ManagedEnvVar
from app.schemas.ops import EnvRenderResult, EnvVarItem
from app.services.ops import ops_audit

# 편집/삭제 하드 제외 키 — 조회엔 노출(editable=False)되나 쓰기는 거부.
EXCLUDED_KEYS: frozenset[str] = frozenset({"JWT_SECRET_KEY", "DATABASE_URL", "REDIS_URL"})


@dataclass(frozen=True)
class _KeySpec:
    is_secret: bool
    kind: str  # bool | int | float | url | json_list | str


# 편집 가능 키 allowlist(앱 레벨 설정 위주). config.py 필드 참고.
ALLOWED_KEYS: dict[str, _KeySpec] = {
    "CORS_ORIGINS": _KeySpec(is_secret=False, kind="json_list"),
    "PUBLIC_API_URL": _KeySpec(is_secret=False, kind="url"),
    "FRONTEND_URL": _KeySpec(is_secret=False, kind="url"),
    "LOG_LEVEL": _KeySpec(is_secret=False, kind="str"),
    "ANTHROPIC_MODEL_DEFAULT": _KeySpec(is_secret=False, kind="str"),
    "ANTHROPIC_MODEL_ADVANCED": _KeySpec(is_secret=False, kind="str"),
    "ANTHROPIC_MODEL_LIGHT": _KeySpec(is_secret=False, kind="str"),
    "OPENAI_MODEL_DEFAULT": _KeySpec(is_secret=False, kind="str"),
    "LLM_ROUTE_COMPLEXITY_THRESHOLD": _KeySpec(is_secret=False, kind="float"),
    "FEATURE_OPS_PANEL": _KeySpec(is_secret=False, kind="bool"),
    "FEATURE_MODERNIZE_ENABLED": _KeySpec(is_secret=False, kind="bool"),
    "FEATURE_LLM_GATEWAY": _KeySpec(is_secret=False, kind="bool"),
    "FEATURE_TEMPORAL": _KeySpec(is_secret=False, kind="bool"),
    "ANTHROPIC_API_KEY": _KeySpec(is_secret=True, kind="str"),
    "OPENAI_API_KEY": _KeySpec(is_secret=True, kind="str"),
    "GITHUB_APP_WEBHOOK_SECRET": _KeySpec(is_secret=True, kind="str"),
    "GOVERNANCE_SERVICE_TOKEN": _KeySpec(is_secret=True, kind="str"),
}

_MAX_VALUE_LEN = 4096
_MASK = "***"
_DISPLAY_TRUNCATE = 200
_ALLOWED_URL_SCHEMES = ("http://", "https://")


# ---------------------------------------------------------------------------
# 검증
# ---------------------------------------------------------------------------


def _validate(key: str, value: str) -> None:
    """쓰기 값 검증. 실패 시 AppError(400).

    - 편집 제외 키 거부
    - allowlist 밖 키 거부
    - 개행 차단 / 크기 상한 / kind 별 형식 검사
    """
    if key in EXCLUDED_KEYS:
        raise AppError(
            "OPS_ENV_KEY_EXCLUDED",
            f"'{key}' 는 편집이 금지된 키입니다(시스템 무결성 보호).",
            400,
        )
    spec = ALLOWED_KEYS.get(key)
    if spec is None:
        raise AppError(
            "OPS_ENV_KEY_NOT_ALLOWED",
            f"'{key}' 는 관리 대상 키가 아닙니다.",
            400,
        )
    if "\n" in value or "\r" in value:
        raise AppError("OPS_ENV_VALUE_INVALID", "값에 개행 문자를 포함할 수 없습니다.", 400)
    if len(value) > _MAX_VALUE_LEN:
        raise AppError(
            "OPS_ENV_VALUE_TOO_LARGE",
            f"값이 최대 길이({_MAX_VALUE_LEN})를 초과했습니다.",
            400,
        )
    _validate_kind(key, value, spec.kind)


def _validate_kind(key: str, value: str, kind: str) -> None:
    if kind == "bool":
        if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
            raise AppError(
                "OPS_ENV_VALUE_INVALID",
                f"'{key}' 는 boolean(true/false) 값이어야 합니다.",
                400,
            )
    elif kind == "int":
        try:
            int(value)
        except ValueError as exc:
            raise AppError("OPS_ENV_VALUE_INVALID", f"'{key}' 는 정수여야 합니다.", 400) from exc
    elif kind == "float":
        try:
            float(value)
        except ValueError as exc:
            raise AppError("OPS_ENV_VALUE_INVALID", f"'{key}' 는 숫자여야 합니다.", 400) from exc
    elif kind == "url":
        if not value.startswith(_ALLOWED_URL_SCHEMES):
            raise AppError(
                "OPS_ENV_VALUE_INVALID",
                f"'{key}' 는 http(s):// URL 이어야 합니다.",
                400,
            )
    elif kind == "json_list":
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise AppError(
                "OPS_ENV_VALUE_INVALID",
                f"'{key}' 는 JSON 배열 문자열이어야 합니다.",
                400,
            ) from exc
        if not isinstance(parsed, list):
            raise AppError("OPS_ENV_VALUE_INVALID", f"'{key}' 는 JSON 배열이어야 합니다.", 400)


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------


async def _rows_by_key(db: AsyncSession) -> dict[str, ManagedEnvVar]:
    result = await db.execute(select(ManagedEnvVar))
    return {str(row.key): row for row in result.scalars().all()}


def _display_value(is_secret: bool, has_value: bool, plaintext: str | None) -> str | None:
    if not has_value:
        return None
    if is_secret:
        return _MASK
    if plaintext is None:
        return None
    if len(plaintext) > _DISPLAY_TRUNCATE:
        return plaintext[: _DISPLAY_TRUNCATE - 1] + "…"
    return plaintext


async def list_env(db: AsyncSession) -> list[EnvVarItem]:
    """제외 키(editable=False) + allowlist 키(editable=True) 의 조회 목록."""
    rows = await _rows_by_key(db)
    pending = await _pending_keys(db, rows)
    items: list[EnvVarItem] = []

    # 제외 키 — 정보성 노출(값은 시크릿 취급, 편집 불가).
    for key in sorted(EXCLUDED_KEYS):
        settings_val = getattr(settings, key.lower(), "") or ""
        items.append(
            EnvVarItem(
                key=key,
                has_value=bool(settings_val),
                is_secret=True,
                editable=False,
                masked_value=_MASK if settings_val else None,
                updated_at=None,
                updated_by=None,
                pending=False,
            )
        )

    # allowlist 키.
    for key, spec in ALLOWED_KEYS.items():
        row = rows.get(key)
        has_value = row is not None
        plaintext = None
        if row is not None and not spec.is_secret:
            plaintext = crypto.decrypt(str(row.value_encrypted))
        items.append(
            EnvVarItem(
                key=key,
                has_value=has_value,
                is_secret=spec.is_secret,
                editable=True,
                masked_value=_display_value(spec.is_secret, has_value, plaintext),
                updated_at=row.updated_at if row is not None else None,
                updated_by=row.updated_by if row is not None else None,
                pending=key in pending,
            )
        )
    return items


# ---------------------------------------------------------------------------
# 쓰기 (upsert / delete)
# ---------------------------------------------------------------------------


async def upsert(db: AsyncSession, key: str, value: str, actor_id: UUID) -> None:
    """검증 → Fernet 암호화 저장 → 감사. 제외/미허용 키는 400."""
    _validate(key, value)
    spec = ALLOWED_KEYS[key]

    result = await db.execute(select(ManagedEnvVar).where(ManagedEnvVar.key == key))
    row = result.scalar_one_or_none()
    old_plain: str | None = None
    if row is None:
        row = ManagedEnvVar(
            key=key,
            value_encrypted=crypto.encrypt(value),
            is_secret=spec.is_secret,
            updated_by=actor_id,
        )
        db.add(row)
    else:
        old_plain = crypto.decrypt(str(row.value_encrypted))
        row.value_encrypted = crypto.encrypt(value)  # type: ignore[assignment]
        row.is_secret = spec.is_secret  # type: ignore[assignment]
        row.updated_by = actor_id  # type: ignore[assignment]

    db.add(
        ops_audit.build_ops_audit(
            actor_id=actor_id,
            action="ops.env.upsert",
            resource=f"managed_env:{key}",
            key=key,
            old_value=old_plain,
            new_value=value,
            is_secret=spec.is_secret,
        )
    )
    await db.commit()


async def delete(db: AsyncSession, key: str, actor_id: UUID) -> None:
    """관리형 키 삭제. 제외/미허용 키는 400, 미존재는 404."""
    if key in EXCLUDED_KEYS:
        raise AppError(
            "OPS_ENV_KEY_EXCLUDED",
            f"'{key}' 는 삭제가 금지된 키입니다.",
            400,
        )
    if key not in ALLOWED_KEYS:
        raise AppError(
            "OPS_ENV_KEY_NOT_ALLOWED",
            f"'{key}' 는 관리 대상 키가 아닙니다.",
            400,
        )
    result = await db.execute(select(ManagedEnvVar).where(ManagedEnvVar.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        raise AppError("OPS_ENV_KEY_NOT_FOUND", f"'{key}' 값이 없습니다.", 404)

    old_plain = crypto.decrypt(str(row.value_encrypted))
    await db.delete(row)
    db.add(
        ops_audit.build_ops_audit(
            actor_id=actor_id,
            action="ops.env.delete",
            resource=f"managed_env:{key}",
            key=key,
            old_value=old_plain,
            new_value=None,
            is_secret=ALLOWED_KEYS[key].is_secret,
        )
    )
    await db.commit()


# ---------------------------------------------------------------------------
# 렌더 / pending (수동 적용)
# ---------------------------------------------------------------------------


def _state_path() -> Path:
    return Path(settings.managed_env_path + ".state.json")


def _secure_write(path: Path, data: bytes) -> None:
    """소유자 전용(0o600) 권한으로 파일을 원자적 성격에 준해 기록.

    - `os.fchmod(fd, 0o600)` 로 **기존 파일이어도** 권한을 강제(O_CREAT mode 는 신규
      생성 시에만 적용되므로, 기존 파일의 group/other 읽기 권한이 남아 평문 시크릿이
      노출되는 것을 방지).
    - `O_NOFOLLOW` 로 심링크 스왑을 통한 임의 경로 덮어쓰기를 차단.
    """
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, data)
    finally:
        os.close(fd)


def _iso(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _read_state() -> dict[str, str]:
    """마지막 렌더 스냅샷(key → updated_at iso). 없으면 빈 dict."""
    path = _state_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    keys = data.get("keys", {})
    if not isinstance(keys, dict):
        return {}
    return {str(k): str(v) for k, v in keys.items()}


async def _pending_keys(db: AsyncSession, rows: dict[str, ManagedEnvVar] | None = None) -> set[str]:
    """마지막 렌더 이후 변경/추가/삭제되어 미적용인 관리형 키 집합."""
    if rows is None:
        rows = await _rows_by_key(db)
    current = {k: _iso(v.updated_at) for k, v in rows.items() if k in ALLOWED_KEYS}
    snapshot = _read_state()
    pending: set[str] = set()
    for key, ts in current.items():
        if snapshot.get(key) != ts:
            pending.add(key)
    # 렌더된 파일엔 있으나 DB 에서 삭제된 키(제거 미적용).
    for key in snapshot:
        if key not in current:
            pending.add(key)
    return pending


async def pending_changes(db: AsyncSession) -> list[str]:
    """미적용 관리형 키 목록(정렬)."""
    return sorted(await _pending_keys(db))


def _recreate_command() -> tuple[str, list[str]]:
    services = list(settings.ops_managed_services)
    base = "docker compose -f docker/docker-compose.prod.yml up -d --no-build --force-recreate"
    if services:
        return f"{base} {' '.join(services)}", services
    return f"{base}  # ops_managed_services 미설정 — 대상 서비스명을 지정하세요", services


async def render_to_file(db: AsyncSession, actor_id: UUID) -> EnvRenderResult:
    """관리형 키를 복호화해 managed_env_path 로 KEY=VALUE 렌더.

    재생성 명령 문자열만 반환하며 docker/재생성은 실행하지 않는다(이 모듈은 docker 미의존).
    """
    rows = await _rows_by_key(db)
    managed = {k: v for k, v in rows.items() if k in ALLOWED_KEYS}

    lines: list[str] = []
    snapshot_keys: dict[str, str] = {}
    for key in sorted(managed):
        row = managed[key]
        plain = crypto.decrypt(str(row.value_encrypted))
        lines.append(f"{key}={plain}")
        snapshot_keys[key] = _iso(row.updated_at)

    now = datetime.now(UTC)
    target = Path(settings.managed_env_path)
    # 시크릿 env 디렉토리 권한을 좁힌다(소유자 전용).
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = "\n".join(lines)
    if content:
        content += "\n"
    # 파일 + 스냅샷 모두 0o600 강제(기존 파일 권한 유지 방지) + 심링크 스왑 차단.
    _secure_write(target, content.encode("utf-8"))
    state = {"rendered_at": now.isoformat(), "keys": snapshot_keys}
    _secure_write(_state_path(), json.dumps(state, ensure_ascii=False).encode("utf-8"))

    command, services = _recreate_command()
    db.add(
        ops_audit.build_ops_audit(
            actor_id=actor_id,
            action="ops.env.render",
            resource=f"managed_env_file:{target}",
            key="render",
            old_value=None,
            new_value=f"{len(managed)} keys",
            is_secret=False,
        )
    )
    await db.commit()

    return EnvRenderResult(
        rendered_path=str(target),
        rendered_at=now,
        applied_count=len(managed),
        recreate_command=command,
        services=services,
        pending=sorted(await _pending_keys(db, rows)),
    )
