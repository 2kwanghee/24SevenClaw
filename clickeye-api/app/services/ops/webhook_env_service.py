"""webhook 수신부 관리형 env 렌더 서비스 (CE-421, superadmin 전용).

정책 요약:
- 인터넷 노출 수신 컨테이너(clickeye-webhook)는 **DB 를 모른다**(최소권한). 프로젝트별
  signing secret 을 팀 ID 에 바인딩한 `WEBHOOK_SECRET_MAP` 을 파일로 내려주는 주체는
  이 API 이며, 수신부는 기동 시 파일을 1회 읽을 뿐이다.
- **MAP 라인만 소유한다**: 운영자가 수기로 관리해 온 주석 / `WEBHOOK_SECRET=` /
  `WEBHOOK_SECRETS=` 라인은 그대로 보존하고 `WEBHOOK_SECRET_MAP=` 라인만 교체한다.
- **fail-closed 제외**: 수신부 파서(`scripts/webhook_server.py:_parse_secret_map`)는
  콤마로 항목을, 첫 `=` 로 팀/시크릿을 자르고 양쪽을 trim 한다. 이 규칙을 깨는 값
  (콤마·개행·team_id 내 `=`·앞뒤 공백)은 **그 항목만 제외**한다. 그대로 렌더하면 인접
  항목까지 오분해되어 무관한 프로젝트가 조용히 거부 상태가 되기 때문.
- **적용은 수동**: 재기동 명령 문자열만 반환하며 docker 를 import 하지도 호출하지도
  않는다(api.env 렌더와 동일 철학).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import AppError
from app.models.project import Project
from app.models.project_linear_credentials import ProjectLinearCredentials
from app.schemas.ops import (
    WebhookEnvProjectItem,
    WebhookEnvRenderResult,
    WebhookEnvSkippedItem,
    WebhookEnvStatus,
)
from app.services.ops import ops_audit
from app.services.ops.env_service import _secure_write

_MAP_KEY = "WEBHOOK_SECRET_MAP"
_LEGACY_KEYS = ("WEBHOOK_SECRET", "WEBHOOK_SECRETS")

_HEADER = (
    "# ClickEye webhook 수신부 관리형 env (CE-421)\n"
    f"# {_MAP_KEY} 라인은 운영 패널이 렌더한다 — 수기로 편집해도 다음 렌더에서 덮어쓴다.\n"
    "# 그 외 라인(주석 / WEBHOOK_SECRET / WEBHOOK_SECRETS)은 렌더가 보존한다.\n"
)


# ---------------------------------------------------------------------------
# 파일 파싱 (렌더 대상 파일의 현재 상태)
# ---------------------------------------------------------------------------


def _target_path() -> Path:
    return Path(settings.webhook_env_path)


def _read_lines(path: Path) -> list[str] | None:
    """파일 라인 목록. 파일이 없으면 None. 읽기 실패는 500 으로 승격."""
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AppError(
            "OPS_WEBHOOK_ENV_READ_FAILED",
            f"webhook env 파일을 읽을 수 없습니다: {path}",
            500,
        ) from exc


def _is_assignment(line: str, key: str) -> bool:
    return line.lstrip().startswith(f"{key}=")


def _assigned_value(line: str) -> str:
    return line.split("=", 1)[1].strip()


def _has_map_line(lines: list[str] | None) -> bool:
    return any(_is_assignment(line, _MAP_KEY) for line in lines or [])


def _has_legacy_secret(lines: list[str] | None) -> bool:
    """값이 실제로 채워진 WEBHOOK_SECRET(S) 라인이 있는지.

    빈 값(`WEBHOOK_SECRET=`)은 example 파일의 기본 형태이며 수신부에서 무효 항목으로
    떨어지므로 경고 대상이 아니다 — "팀 검사를 받지 않는 시크릿이 살아 있는가" 만 본다.
    """
    for line in lines or []:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for key in _LEGACY_KEYS:
            if _is_assignment(stripped, key) and _assigned_value(stripped):
                return True
    return False


# ---------------------------------------------------------------------------
# 항목 검증 (수신부 파서 계약)
# ---------------------------------------------------------------------------


def _skip_reason(team_id: str, secret: str) -> str | None:
    """MAP 항목으로 안전한지 판정. 안전하면 None, 아니면 사유(시크릿 값 미포함)."""
    for label, value in (("team_id", team_id), ("시크릿", secret)):
        if not value:
            return f"{label} 가 비어 있음"
        if "," in value:
            return f"{label} 에 콤마(,) 포함 — 수신부 파서가 항목 경계로 분해함"
        if "\n" in value or "\r" in value:
            return f"{label} 에 개행 포함 — env 라인이 분리됨"
        if value != value.strip():
            return f"{label} 앞뒤에 공백 포함 — 수신부가 trim 하여 저장값과 달라짐"
    if "=" in team_id:
        return "team_id 에 '=' 포함 — 수신부가 팀/시크릿 경계를 잘못 자름"
    return None


# ---------------------------------------------------------------------------
# 조회
# ---------------------------------------------------------------------------


async def _credential_rows(db: AsyncSession) -> list[tuple[ProjectLinearCredentials, str]]:
    """Linear 자격증명 + 프로젝트명. team_id → 프로젝트명 순으로 결정적 정렬."""
    result = await db.execute(
        select(ProjectLinearCredentials, Project.name)
        .join(Project, Project.id == ProjectLinearCredentials.project_id)
        .order_by(ProjectLinearCredentials.team_id, Project.name)
    )
    return [(row, str(name)) for row, name in result.all()]


async def preview(db: AsyncSession) -> WebhookEnvStatus:
    """렌더 대상 파일 상태 + MAP 후보 목록(시크릿 평문 미반환)."""
    path = _target_path()
    lines = _read_lines(path)
    rows = await _credential_rows(db)
    return WebhookEnvStatus(
        rendered_path=str(path),
        file_exists=lines is not None,
        map_line_present=_has_map_line(lines),
        legacy_present=_has_legacy_secret(lines),
        projects=[
            WebhookEnvProjectItem(
                project_id=row.project_id,
                project_name=name,
                team_id=str(row.team_id or ""),
                has_secret=bool((row.webhook_secret or "").strip()),
            )
            for row, name in rows
        ],
    )


# ---------------------------------------------------------------------------
# 렌더
# ---------------------------------------------------------------------------


def _restart_command() -> str:
    return (
        "docker compose -f clickeye-infra/docker/docker-compose.yml "
        "up -d --no-build --force-recreate webhook"
    )


def _apply_map_line(lines: list[str] | None, map_line: str) -> list[str]:
    """MAP 라인만 교체/추가하고 나머지 라인은 원문 그대로 보존.

    중복 MAP 라인이 있으면 첫 라인 자리에서 교체하고 나머지는 제거한다(수신부는 마지막
    값만 보므로 중복이 남으면 렌더 결과와 실제 적용값이 어긋난다).
    """
    if lines is None:
        return _HEADER.splitlines() + [map_line]

    out: list[str] = []
    replaced = False
    for line in lines:
        if _is_assignment(line, _MAP_KEY):
            if not replaced:
                out.append(map_line)
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(map_line)
    return out


async def render(db: AsyncSession, actor_id: UUID) -> WebhookEnvRenderResult:
    """DB 의 프로젝트별 signing secret 을 WEBHOOK_SECRET_MAP 으로 렌더.

    재기동 명령 문자열만 반환하며 docker 는 실행하지 않는다.
    """
    rows = await _credential_rows(db)

    entries: list[str] = []
    skipped: list[WebhookEnvSkippedItem] = []
    for row, name in rows:
        secret = row.webhook_secret or ""
        if not secret.strip():
            # 시크릿 미등록 프로젝트는 MAP 대상이 아니다(제외 사유로 보고하지 않음).
            continue
        team_id = str(row.team_id or "")
        reason = _skip_reason(team_id, str(secret))
        if reason is not None:
            skipped.append(
                WebhookEnvSkippedItem(
                    project_id=row.project_id,
                    project_name=name,
                    team_id=team_id,
                    reason=reason,
                )
            )
            continue
        entries.append(f"{team_id}={secret}")

    # team_id 정렬로 결정적 출력. 같은 팀의 시크릿이 둘 이상이면 모두 남긴다(로테이션).
    entries.sort()
    map_line = f"{_MAP_KEY}={','.join(entries)}"

    path = _target_path()
    lines = _read_lines(path)
    rendered = _apply_map_line(lines, map_line)

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = "\n".join(rendered)
    if content:
        content += "\n"
    _secure_write(path, content.encode("utf-8"))

    now = datetime.now(UTC)
    db.add(
        ops_audit.build_ops_audit(
            actor_id=actor_id,
            action="ops.env.webhook_render",
            resource=f"webhook_env_file:{path}",
            key="webhook_render",
            old_value=None,
            new_value=f"{len(entries)} entries, {len(skipped)} skipped",
            is_secret=False,
        )
    )
    await db.commit()

    return WebhookEnvRenderResult(
        rendered_path=str(path),
        rendered_at=now,
        entry_count=len(entries),
        skipped=skipped,
        legacy_present=_has_legacy_secret(rendered),
        restart_command=_restart_command(),
    )
