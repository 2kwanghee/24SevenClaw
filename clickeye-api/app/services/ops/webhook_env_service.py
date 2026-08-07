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
- **항목 0개면 라인을 지운다**: 빈 `WEBHOOK_SECRET_MAP=` 는 수신부에 "설정했는데 유효
  항목 0개"로 읽혀 기동 거부를 유발한다. 그래서 항목이 없으면 라인 자체를 제거해 미설정
  상태로 되돌린다(폐기 시크릿도 함께 사라진다).
- **드리프트는 파일이 진실**: 별도 스냅샷 파일 없이 파일의 MAP 항목 집합과 DB 산출 집합을
  직접 비교해 미반영 변경을 보고한다.
- **적용은 수동**: 재기동 명령 문자열만 반환하며 docker 를 import 하지도 호출하지도
  않는다(api.env 렌더와 동일 철학).
"""

from __future__ import annotations

import os
import re
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
    WebhookEnvDriftItem,
    WebhookEnvProjectItem,
    WebhookEnvRenderResult,
    WebhookEnvSkippedItem,
    WebhookEnvStatus,
)
from app.services.ops import ops_audit

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


def _assignment_re(key: str) -> re.Pattern[str]:
    """`KEY=` 뿐 아니라 `export KEY=` · `KEY = ` 형태까지 같은 할당으로 인식한다.

    단순 `startswith(f"{key}=")` 는 이 변형들을 놓치므로, 수기로 `export
    WEBHOOK_SECRET_MAP=...` 를 써 둔 파일에서 렌더가 새 라인을 덧붙이고 옛 라인이 그대로
    남는다. env_file 은 뒤 라인이 이기므로 **폐기 시크릿이 계속 유효**해진다.
    """
    return re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")


_MAP_ASSIGN_RE = _assignment_re(_MAP_KEY)
_LEGACY_ASSIGN_RES = tuple(_assignment_re(key) for key in _LEGACY_KEYS)


def _assigned_value(line: str) -> str:
    return line.split("=", 1)[1].strip()


def _has_map_line(lines: list[str] | None) -> bool:
    return any(_MAP_ASSIGN_RE.match(line) for line in lines or [])


def _file_map_entries(lines: list[str] | None) -> dict[str, set[str]]:
    """파일의 MAP 라인을 **수신부와 같은 규칙**으로 파싱해 team_id → 시크릿 집합으로.

    `scripts/webhook_server.py:_parse_secret_map` 계약: 콤마로 항목, 첫 `=` 로 팀/시크릿을
    자르고 양쪽 trim, 한쪽이라도 비면 그 항목은 무효. MAP 라인이 여럿이면 env_file 의
    "뒤 라인이 이긴다" 규칙대로 **마지막 라인만** 본다.
    """
    raw: str | None = None
    for line in lines or []:
        if _MAP_ASSIGN_RE.match(line):
            raw = _assigned_value(line)
    if not raw:
        return {}
    entries: dict[str, set[str]] = {}
    for item in raw.split(","):
        team, sep, secret = item.partition("=")
        if not sep:
            continue
        team, secret = team.strip(), secret.strip()
        if not team or not secret:
            continue
        entries.setdefault(team, set()).add(secret)
    return entries


def _has_legacy_secret(lines: list[str] | None) -> bool:
    """값이 실제로 채워진 WEBHOOK_SECRET(S) 라인이 있는지.

    빈 값(`WEBHOOK_SECRET=`)은 example 파일의 기본 형태이며 수신부에서 무효 항목으로
    떨어지므로 경고 대상이 아니다 — "팀 검사를 받지 않는 시크릿이 살아 있는가" 만 본다.
    """
    for line in lines or []:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        for pattern in _LEGACY_ASSIGN_RES:
            if pattern.match(stripped) and _assigned_value(stripped):
                return True
    return False


# ---------------------------------------------------------------------------
# 항목 검증 (수신부 파서 계약)
# ---------------------------------------------------------------------------


def _is_single_physical_line(value: str) -> bool:
    """`value` 가 env 파일에서 정확히 물리 1라인으로 남는지.

    `"\\n" in value` 같은 블랙리스트는 `\\x0b`(VT) · `\\x85`(NEL) · `\\u2028`(LS) 처럼
    **Python `splitlines()` 가 줄로 인정하지만 `\\n` 이 아닌** 문자를 통과시킨다. 그런 값이
    한 번 파일에 들어가면 다음 렌더가 `read_text().splitlines()` 로 재파싱하며 독립 라인으로
    분해되어(`WEBHOOK_SECRET=…` 주입) 영구 잔존한다. 그래서 "쓰는 쪽"이 아니라 "읽는 쪽"과
    동일한 함수로 판정한다 — splitlines 가 줄로 인정하는 모든 문자를 자동으로 커버한다.
    """
    return value.splitlines() == [value]


def _has_control_char(value: str) -> bool:
    """C0 제어문자 / DEL 포함 여부(splitlines 검사와 일부 중복되나 의도적)."""
    return any(ch < " " or ch == "\x7f" for ch in value)


def _skip_reason(team_id: str, secret: str) -> str | None:
    """MAP 항목으로 안전한지 판정. 안전하면 None, 아니면 사유(시크릿 값 미포함)."""
    for label, value in (("team_id", team_id), ("시크릿", secret)):
        if not value:
            return f"{label} 가 비어 있음"
        if not _is_single_physical_line(value):
            return f"{label} 에 줄바꿈 문자 포함 — env 라인이 분리되어 임의 키가 주입됨"
        if _has_control_char(value):
            return f"{label} 에 제어문자 포함 — env 라인으로 안전하지 않음"
        if "," in value:
            return f"{label} 에 콤마(,) 포함 — 수신부 파서가 항목 경계로 분해함"
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


def _build_entries(
    rows: list[tuple[ProjectLinearCredentials, str]],
) -> tuple[list[str], list[WebhookEnvSkippedItem]]:
    """DB 행에서 MAP 항목 문자열 목록과 fail-closed 제외 목록을 산출(정렬된 결정적 출력).

    같은 team_id 를 가진 항목이 둘 이상이면 **전부** 남긴다. 수신부는 시크릿을 팀에만
    바인딩하므로(프로젝트 개념이 없음) 이는 로테이션뿐 아니라 **같은 Linear 팀을 공유하는
    서로 다른 프로젝트**에도 해당한다 — 그 경우 한 프로젝트의 시크릿으로 서명한 요청이 같은
    팀의 다른 프로젝트 이벤트로도 통과한다. 수신부 의미론상 불가피하며, 테넌트 격리가
    필요하면 팀을 분리해야 한다.
    """
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
    entries.sort()
    return entries, skipped


def _entries_by_team(entries: list[str]) -> dict[str, set[str]]:
    grouped: dict[str, set[str]] = {}
    for entry in entries:
        team, _, secret = entry.partition("=")
        grouped.setdefault(team, set()).add(secret)
    return grouped


def _drift(
    file_entries: dict[str, set[str]], desired: dict[str, set[str]]
) -> list[WebhookEnvDriftItem]:
    """파일과 DB 산출 결과의 차이. 스냅샷 파일 없이 **파일 자체를 진실로** 비교한다.

    시크릿 값은 비교에만 쓰고 결과에는 team_id 와 상태 라벨만 담는다.
    """
    items: list[WebhookEnvDriftItem] = []
    for team in sorted(set(file_entries) | set(desired)):
        in_file, in_db = file_entries.get(team), desired.get(team)
        if in_db is None:
            # 파일에만 남은 팀 = 자격증명이 지워졌는데 수신부에서는 아직 유효한 폐기 시크릿.
            items.append(WebhookEnvDriftItem(team_id=team, state="removed"))
        elif in_file is None:
            items.append(WebhookEnvDriftItem(team_id=team, state="added"))
        elif in_file != in_db:
            items.append(WebhookEnvDriftItem(team_id=team, state="changed"))
    return items


def _warnings(entry_count: int, legacy_present: bool) -> list[str]:
    """항목 0개 상황의 운영 경고 코드(문구는 프론트가 i18n).

    항목이 0개면 MAP 라인 자체를 쓰지 않는다. 그 상태에서 레거시 WEBHOOK_SECRET(S) 도
    없으면 수신부는 유효 시크릿 0개로 **기동을 거부**한다(webhook_server.main fail-closed).
    즉 재기동 명령을 그대로 실행하면 수신부가 내려간다.
    """
    if entry_count > 0:
        return []
    codes = ["map_line_removed"]
    if not legacy_present:
        codes.append("receiver_startup_blocked")
    return codes


async def preview(db: AsyncSession) -> WebhookEnvStatus:
    """렌더 대상 파일 상태 + MAP 후보 목록 + 미반영 드리프트(시크릿 평문 미반환)."""
    path = _target_path()
    lines = _read_lines(path)
    rows = await _credential_rows(db)

    entries, _ = _build_entries(rows)
    file_entries = _file_map_entries(lines)
    legacy_present = _has_legacy_secret(lines)
    file_entry_count = sum(len(secrets) for secrets in file_entries.values())

    return WebhookEnvStatus(
        rendered_path=str(path),
        file_exists=lines is not None,
        map_line_present=_has_map_line(lines),
        legacy_present=legacy_present,
        projects=[
            WebhookEnvProjectItem(
                project_id=row.project_id,
                project_name=name,
                team_id=str(row.team_id or ""),
                has_secret=bool((row.webhook_secret or "").strip()),
            )
            for row, name in rows
        ],
        file_entry_count=file_entry_count,
        expected_entry_count=len(entries),
        drift=_drift(file_entries, _entries_by_team(entries)),
        warnings=_warnings(len(entries), legacy_present),
    )


# ---------------------------------------------------------------------------
# 렌더
# ---------------------------------------------------------------------------


def _atomic_secure_write(path: Path, data: bytes) -> None:
    """0o600 임시 파일에 쓴 뒤 `os.replace` 로 원자적 교체.

    수신부는 기동 시 이 파일을 1회 읽으므로, 렌더와 기동이 겹치면 `O_TRUNC` 방식은 반쯤
    쓰인 파일(= MAP 항목 일부 누락)을 읽히는 창이 있다. 교체는 원자적이라 그 창이 없다.

    보안 성질은 `env_service._secure_write` 와 동일하게 유지한다 — 임시 파일은
    `O_EXCL | O_NOFOLLOW` 로 같은 디렉터리(0o700)에 만들고 `fchmod(0o600)` 를 강제한다.
    `os.replace` 는 심링크를 **따라가지 않고 교체**하므로 심링크 스왑으로 임의 경로를
    덮어쓸 수 없다.
    """
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    try:
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def _restart_command() -> str:
    """webhook 서비스 재생성 명령.

    `webhook` 서비스는 `clickeye-infra/docker/docker-compose.yml` 에만 정의돼 있다
    (`docker-compose.prod.yml` 에는 db/redis/migrate/api/web/dockerproxy 뿐 — webhook 없음).
    형제 렌더인 `env_service._recreate_command()` 는 `docker/docker-compose.prod.yml` 로
    안내하므로 **CWD 를 clickeye-infra 로 가정**한다. 그 기준을 그대로 승계하되, 두 카드가
    같은 화면에 있어 오실행 위험이 있으므로 실행 위치를 명령에 명시한다.
    """
    return (
        "cd clickeye-infra && docker compose -f docker/docker-compose.yml "
        "up -d --no-build --force-recreate webhook"
    )


_ENV_LINE_RE = re.compile(r"^\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=")


def _is_preservable(line: str) -> bool:
    """보존해도 되는 기존 라인인지 — 빈 줄 / 주석 / 정상 `KEY=VALUE` 만 허용.

    렌더는 MAP 이외 라인을 보존하므로, 과거에 주입된 오염 라인이 있으면 그것까지 영구히
    되쓴다. 보존 시점에 다시 구조를 검사해 그 외 형태(제어문자 포함 라인 등)를 드롭하면
    이미 오염된 파일도 렌더 1회로 스스로 정화된다.
    """
    if _has_control_char(line):
        return False
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return True
    return _ENV_LINE_RE.match(line) is not None


def _apply_map_line(lines: list[str] | None, map_line: str | None) -> tuple[list[str], int]:
    """MAP 라인만 교체/추가/제거하고 나머지 **정상 형태** 라인은 원문 그대로 보존.

    중복 MAP 라인이 있으면 첫 라인 자리에서 교체하고 나머지는 제거한다(수신부는 마지막
    값만 보므로 중복이 남으면 렌더 결과와 실제 적용값이 어긋난다).

    `map_line` 이 None 이면(= 렌더 항목 0개) 기존 MAP 라인을 **제거만** 한다. 빈
    `WEBHOOK_SECRET_MAP=` 를 쓰면 수신부가 "MAP 설정 의도는 있는데 유효 항목 0개"로 보고
    기동을 거부한다(webhook_server.main). 라인 자체를 없애면 "MAP 미설정"으로 판정되어
    레거시 등 다른 소스가 있으면 정상 기동한다 — 그러면서도 폐기 시크릿은 남기지 않는다.

    반환: (렌더 라인 목록, 드롭한 오염 라인 수).
    """
    if lines is None:
        return _HEADER.splitlines() + ([map_line] if map_line is not None else []), 0

    out: list[str] = []
    dropped = 0
    replaced = False
    for line in lines:
        if _MAP_ASSIGN_RE.match(line):
            if map_line is not None and not replaced:
                out.append(map_line)
                replaced = True
            continue
        if not _is_preservable(line):
            # 시크릿이 섞여 있을 수 있으므로 내용은 로그·응답 어디에도 남기지 않는다.
            dropped += 1
            continue
        out.append(line)
    if map_line is not None and not replaced:
        out.append(map_line)
    return out, dropped


async def render(db: AsyncSession, actor_id: UUID) -> WebhookEnvRenderResult:
    """DB 의 프로젝트별 signing secret 을 WEBHOOK_SECRET_MAP 으로 렌더.

    재기동 명령 문자열만 반환하며 docker 는 실행하지 않는다.
    """
    rows = await _credential_rows(db)
    entries, skipped = _build_entries(rows)

    # 항목이 0개면 빈 MAP 라인을 쓰지 않고 제거한다(_apply_map_line 참조 — 수신부 fail-closed).
    map_line = f"{_MAP_KEY}={','.join(entries)}" if entries else None

    path = _target_path()
    lines = _read_lines(path)
    rendered, dropped_line_count = _apply_map_line(lines, map_line)

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    content = "\n".join(rendered)
    if content:
        content += "\n"
    _atomic_secure_write(path, content.encode("utf-8"))

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

    legacy_present = _has_legacy_secret(rendered)
    return WebhookEnvRenderResult(
        rendered_path=str(path),
        rendered_at=now,
        entry_count=len(entries),
        dropped_line_count=dropped_line_count,
        skipped=skipped,
        legacy_present=legacy_present,
        warnings=_warnings(len(entries), legacy_present),
        restart_command=_restart_command(),
    )
