"""운영 패널 감사 로그 헬퍼 (쓰기 PR-3/4 에서 사용).

RoleAuditLog 를 재사용하되, 시크릿이 감사 로그로 유출되지 않도록 값을 마스킹하고
컬럼 길이(String(100))에 맞춰 절단한다. 이번 PR(읽기 전용)은 쓰기 경로가 없어
호출처가 없으나, 후속 env/table CRUD 가 즉시 사용할 수 있도록 최소 구현을 제공한다.
"""

from __future__ import annotations

from uuid import UUID

from app.models.rbac import RoleAuditLog

# RoleAuditLog.old_value / new_value 컬럼 상한.
_VALUE_MAX = 100
# 시크릿으로 간주해 마스킹할 키 substring (대소문자 무시).
_SECRET_HINTS = ("secret", "token", "password", "key", "credential")


def is_secret_key(key: str) -> bool:
    """키 이름이 시크릿성 값을 담을 가능성이 높은지 판정."""
    low = key.lower()
    return any(hint in low for hint in _SECRET_HINTS)


def mask_value(key: str, value: str | None) -> str | None:
    """시크릿 키의 값은 마스킹하고, 그 외는 컬럼 길이에 맞춰 절단."""
    if value is None:
        return None
    if is_secret_key(key):
        return "***"
    if len(value) > _VALUE_MAX:
        return value[: _VALUE_MAX - 1] + "…"
    return value


def build_ops_audit(
    *,
    actor_id: UUID,
    action: str,
    resource: str,
    key: str,
    old_value: str | None,
    new_value: str | None,
) -> RoleAuditLog:
    """마스킹/절단이 적용된 운영 감사 로그 엔트리 생성 (DB 추가는 호출처 책임)."""
    return RoleAuditLog(
        actor_id=actor_id,
        target_user_id=None,
        action=action[:50],
        old_value=mask_value(key, old_value),
        new_value=mask_value(key, new_value) or "",
        resource=resource[:100],
    )
