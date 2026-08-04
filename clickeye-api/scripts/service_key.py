"""머신 서비스 키(`X-ClickEye-Service-Key`) 발급·조회·회수 CLI (CE-350).

## 왜 이 CLI 가 필요한가

무인 딜리버리의 실행면(러너·배치)은 헤드리스다. 그런데 그 실행면이 쓰는 자격증명을 얻는
유일한 경로가 `POST /api/v1/intake/service-keys`(`require_superadmin`) 뿐이었다 — 즉 러너를
활성화하려면 사람이 브라우저로 로그인해야 했고, `docs/spec/run_guide.md` 3-6 2단계는 키가
이미 있다고 가정한 채 막혀 있었다(실측 2026-08-04: `workspace_map.py` exit 2). 이 CLI 가 그
전제를 없앤다.

## 이 키가 여는 문 (발급 전 반드시 인지할 것)

`X-ClickEye-Service-Key` 는 세 면의 **공용** 인증 채널이다:
  · 인테이크 접수      POST /api/v1/intake            (app/api/v1/intake.py)
  · 거버넌스 evaluate  POST /api/v1/governance/...    (app/api/v1/governance.py)
  · 머신 조회          워크스페이스 원장 폴링         (scripts/workspace_map.py)
따라서 키 하나를 발급하는 것은 이 세 면의 접근 권한을 만드는 일이다. 평문은 발급 시점
1회만 노출되며 DB 에는 sha256 해시만 남는다(복구 불가 — 잃으면 재발급).

## 사용법

    cd /mnt/c/workspace/ClickEye/clickeye-api

    # 발급 — 평문은 stdout 한 줄만, 안내는 stderr 로 나간다(캡처 안전)
    uv run python -m scripts.service_key issue --name "로컬 러너"
    KEY="$(uv run python -m scripts.service_key issue --name '로컬 러너' 2>/dev/null)"

    # .env 에 붙일 한 줄만 출력
    uv run python -m scripts.service_key issue --name "로컬 러너" --print-env

    # 목록 (해시·평문 미노출)
    uv run python -m scripts.service_key list

    # 회수 — 이후 그 키의 인증은 401. 레코드는 감사용으로 보존된다
    uv run python -m scripts.service_key deactivate --id <uuid>

    # 검증 — 평문을 인자로 받지 않는다(프로세스 목록·셸 히스토리 노출 방지)
    printf '%s' "$KEY" | uv run python -m scripts.service_key verify --stdin
    CLICKEYE_SERVICE_KEY="$KEY" uv run python -m scripts.service_key verify

## 보관 규약

평문을 로그·원장·커밋에 남기지 않는다. 이 스크립트는 `.env` 를 **직접 고치지 않는다**
(비밀을 파일에 쓰는 주체를 늘리지 않기 위해). 등재는 운영자가 아래처럼 한다:

    umask 077
    uv run python -m scripts.service_key issue --name "로컬 러너" --print-env >> ../.env
    grep -c CLICKEYE_SERVICE_KEY ../.env   # 1 이어야 정상(중복 등재 확인)

로테이션: 새 키를 발급해 `.env` 를 교체한 뒤 옛 키를 `deactivate` 한다(순서 중요 — 먼저
내리면 그 사이 배치가 401 로 실패한다).

## 종료 코드

    0  성공
    2  인자·입력 오류(이름 누락, 잘못된 UUID, 빈 평문 등)
    3  대상 없음(deactivate 할 키가 없음) 또는 verify 실패(무효/비활성 키)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from uuid import UUID

from app.core.exceptions import AppError
from app.database import async_session, engine
from app.services.intake_service import IntakeService


def _silence_sql_echo() -> None:
    """SQLAlchemy echo 로그를 끈다.

    `app/database.py:6` 은 `echo=settings.debug` 로 엔진을 만든다. `DEBUG=true` 환경에서는
    SQL 로그가 **stdout** 으로 쏟아져 "stdout 은 평문 한 줄만" 계약이 깨진다(실측:
    `KEY=$(... issue)` 가 SQL 17줄을 캡처했다). INSERT 파라미터에 key_hash 까지 찍히므로
    비밀 위생 문제도 된다.

    로거 레벨을 올리는 것만으로는 막히지 않는다 — echo 는 인스턴스 로거가 레벨을 무시하고
    INFO 로 내보내는 구조다(실측 확인). 엔진의 `echo` 속성을 직접 내려야 한다. 프로세스
    수명이 이 CLI 한 번뿐이므로 전역 상태를 되돌릴 필요는 없다.
    """
    engine.echo = False
    for name in ("sqlalchemy.engine", "sqlalchemy.engine.Engine", "sqlalchemy.pool"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _err(msg: str) -> None:
    """사람에게 보내는 메시지는 전부 stderr — stdout 은 평문 키 전용이다."""
    print(msg, file=sys.stderr)


async def _issue(name: str, organization_id: UUID | None, print_env: bool) -> int:
    # 발급 로직은 서비스가 권위(로직 복제 금지). 해시도 서비스 것을 그대로 쓴다 —
    # 여기서 따로 sha256 하면 서버 검증과 어긋날 여지가 생긴다.
    async with async_session() as db:
        raw, key = await IntakeService(db).create_service_key(name, organization_id)

    _err(f"발급 완료: id={key.id} name={key.name!r} org={key.organization_id} active={key.is_active}")
    _err("평문은 지금 1회만 노출됩니다 — DB 에는 sha256 해시만 저장되며 복구할 수 없습니다.")
    if print_env:
        print(f"CLICKEYE_SERVICE_KEY={raw}")
        _err("위 한 줄을 .env 에 등재하세요(umask 077 권장).")
    else:
        print(raw)
    return 0


async def _list() -> int:
    async with async_session() as db:
        keys = await IntakeService(db).list_service_keys()

    if not keys:
        _err("발급된 서비스 키가 없습니다.")
        return 0
    # 해시·평문은 절대 출력하지 않는다(모델에 key_hash 가 있지만 여기서 읽지 않는다).
    _err(f"{'ID':38} {'ACTIVE':7} {'ORG':38} NAME")
    for k in keys:
        print(f"{str(k.id):38} {str(bool(k.is_active)):7} {str(k.organization_id):38} {k.name}")
    return 0


async def _deactivate(key_id: UUID) -> int:
    async with async_session() as db:
        try:
            key = await IntakeService(db).deactivate_service_key(key_id)
        except AppError as exc:
            _err(f"회수 실패: {exc.message}")
            return 3
    _err(f"회수 완료: id={key.id} name={key.name!r} active={key.is_active}")
    _err("이후 이 키의 인증은 401 입니다(레코드는 감사용으로 보존).")
    return 0


async def _verify(raw: str) -> int:
    async with async_session() as db:
        try:
            key = await IntakeService(db).authenticate_key(raw)
        except AppError as exc:
            _err(f"검증 실패: {exc.message}")
            return 3
    _err(f"검증 성공: id={key.id} name={key.name!r} org={key.organization_id}")
    return 0


def _read_raw(args: argparse.Namespace) -> str | None:
    """평문을 stdin 또는 환경변수에서 읽는다.

    인자(`--key <평문>`)로 받지 않는 이유: 인자는 `ps` 의 cmdline 과 셸 히스토리에 남는다.
    """
    import os

    if args.stdin:
        return sys.stdin.read().strip()
    return (os.environ.get("CLICKEYE_SERVICE_KEY") or "").strip()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="service_key",
        description="머신 서비스 키 발급·조회·회수 (평문은 발급 시 1회만 노출)",
        epilog="상세: 이 파일의 모듈 docstring / docs/spec/run_guide.md 3-6 2단계",
    )
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("issue", help="새 키 발급 — 평문을 stdout 에 1회 출력")
    pi.add_argument("--name", required=True, help="키 라벨(용도 식별용, 예: '로컬 러너')")
    pi.add_argument("--organization", default=None,
                    help="키 소속 조직 UUID(선택). accept 시 생성되는 Project 로 전파된다")
    pi.add_argument("--print-env", action="store_true",
                    help="평문 대신 `CLICKEYE_SERVICE_KEY=<평문>` 한 줄을 출력(.env 등재용)")

    sub.add_parser("list", help="발급 목록(해시·평문 미노출)")

    pd = sub.add_parser("deactivate", help="키 회수 — 이후 인증 401")
    pd.add_argument("--id", required=True, help="회수할 키의 UUID(`list` 로 확인)")

    pv = sub.add_parser("verify", help="평문이 실제로 인증되는지 확인")
    pv.add_argument("--stdin", action="store_true",
                    help="평문을 stdin 으로 받는다(미지정 시 CLICKEYE_SERVICE_KEY 환경변수)")

    return p


async def run_async(argv: list[str] | None = None) -> int:
    """파싱·검증·실행 본체(코루틴).

    `asyncio.run` 을 여기 넣지 않는 이유: 이미 이벤트 루프가 도는 곳(pytest-asyncio 등)에서
    호출하면 `asyncio.run() cannot be called from a running event loop` 로 죽는다. 동기
    진입점은 `main()` 하나로 좁히고, 로직은 이 코루틴에 둔다.
    """
    args = build_parser().parse_args(argv)
    _silence_sql_echo()

    if args.command == "issue":
        if not args.name.strip():
            _err("ERROR: --name 이 비어 있습니다.")
            return 2
        org: UUID | None = None
        if args.organization:
            try:
                org = UUID(args.organization)
            except ValueError:
                _err(f"ERROR: --organization 이 UUID 형식이 아닙니다: {args.organization!r}")
                return 2
        return await _issue(args.name.strip(), org, args.print_env)

    if args.command == "list":
        return await _list()

    if args.command == "deactivate":
        try:
            key_id = UUID(args.id)
        except ValueError:
            _err(f"ERROR: --id 가 UUID 형식이 아닙니다: {args.id!r}")
            return 2
        return await _deactivate(key_id)

    if args.command == "verify":
        raw = _read_raw(args)
        if not raw:
            _err("ERROR: 평문이 비어 있습니다 — --stdin 으로 넘기거나 "
                 "CLICKEYE_SERVICE_KEY 를 설정하세요.")
            return 2
        return await _verify(raw)

    _err(f"ERROR: 알 수 없는 커맨드: {args.command}")
    return 2


def main(argv: list[str] | None = None) -> int:
    """동기 진입점 — 이벤트 루프가 없는 셸 실행 전용."""
    return asyncio.run(run_async(argv))


if __name__ == "__main__":
    sys.exit(main())
