"""머신 서비스 키 CLI (scripts/service_key.py, CE-350) 테스트.

핵심 검증:
- 발급한 평문이 실제로 `authenticate_key` 를 통과한다(= 러너가 그 키로 머신 API 를 쓸 수 있다)
- 회수 후 같은 평문은 인증 실패(401) — soft delete 이므로 레코드는 남는다
- **평문은 stdout 한 줄만** 나가고 안내는 stderr 로 분리된다(`KEY=$(...)` 캡처 안전)
- `--print-env` 는 `.env` 에 붙일 한 줄 형태로 나간다
- `list` 출력에 key_hash·평문이 섞이지 않는다
- 인자 검증: 빈 이름 / 잘못된 UUID → exit 2, 없는 키 회수 → exit 3
- 기존 키 인증은 이 CLI 도입과 무관하게 그대로 동작한다(회귀 0)

Usage:
    cd clickeye-api && uv run pytest tests/test_service_key_cli.py -v
"""

from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.intake import IntakeServiceKey
from app.services.intake_service import IntakeService
from scripts import service_key as cli


@pytest.fixture(autouse=True)
def _use_test_session(monkeypatch, db_session: AsyncSession):
    """CLI 의 `async_session()` 을 테스트 세션으로 갈아끼운다.

    CLI 는 `async with async_session() as db:` 로 자기 세션을 연다. 테스트에서는 같은
    인메모리 DB 를 봐야 하므로, 컨텍스트 매니저 모양만 흉내내는 대역으로 교체한다.
    db_session 을 닫지 않는다(테스트 픽스처가 수명을 소유).
    """

    class _Holder:
        async def __aenter__(self) -> AsyncSession:
            return db_session

        async def __aexit__(self, *_exc) -> bool:
            return False

    monkeypatch.setattr(cli, "async_session", lambda: _Holder())


def _run(argv: list[str]) -> int:
    """동기 테스트용 — 루프가 없으므로 동기 진입점을 그대로 쓴다."""
    return cli.main(argv)


async def _arun(argv: list[str]) -> int:
    """async 테스트용 — 이미 루프가 도는 곳에서 main() 을 부르면 asyncio.run 이 죽는다."""
    return await cli.run_async(argv)


# ---------------------------------------------------------------------------
# 발급 → 인증
# ---------------------------------------------------------------------------


def test_issue_prints_plaintext_on_stdout_only(capsys):
    rc = _run(["issue", "--name", "로컬 러너"])
    assert rc == 0
    out = capsys.readouterr()
    raw = out.out.strip()
    # stdout 은 평문 한 줄만 — 여기에 안내 문구가 섞이면 `KEY=$(...)` 가 오염된다.
    assert "\n" not in raw
    assert len(raw) >= 32
    assert "발급 완료" in out.err  # 안내는 stderr
    assert raw not in out.err  # 평문이 안내에 중복 노출되지 않는다


@pytest.mark.asyncio
async def test_issued_key_authenticates(capsys, db_session: AsyncSession):
    assert await _arun(["issue", "--name", "머신 조회용"]) == 0
    raw = capsys.readouterr().out.strip()

    key = await IntakeService(db_session).authenticate_key(raw)
    assert key.name == "머신 조회용"
    assert bool(key.is_active) is True


@pytest.mark.asyncio
async def test_db_stores_hash_not_plaintext(capsys, db_session: AsyncSession):
    assert await _arun(["issue", "--name", "해시 확인"]) == 0
    raw = capsys.readouterr().out.strip()

    result = await db_session.execute(
        select(IntakeServiceKey).where(IntakeServiceKey.name == "해시 확인")
    )
    row = result.scalar_one()
    assert row.key_hash == hashlib.sha256(raw.encode()).hexdigest()
    assert raw not in str(row.key_hash)


def test_print_env_emits_dotenv_line(capsys):
    assert _run(["issue", "--name", "env 등재", "--print-env"]) == 0
    out = capsys.readouterr().out.strip()
    assert out.startswith("CLICKEYE_SERVICE_KEY=")
    assert len(out.split("=", 1)[1]) >= 32


# ---------------------------------------------------------------------------
# 회수
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivate_blocks_authentication(capsys, db_session: AsyncSession):
    assert await _arun(["issue", "--name", "회수 대상"]) == 0
    raw = capsys.readouterr().out.strip()

    result = await db_session.execute(
        select(IntakeServiceKey).where(IntakeServiceKey.name == "회수 대상")
    )
    row = result.scalar_one()

    assert await _arun(["deactivate", "--id", str(row.id)]) == 0
    assert "회수 완료" in capsys.readouterr().err

    with pytest.raises(AppError) as exc:
        await IntakeService(db_session).authenticate_key(raw)
    assert exc.value.status_code == 401

    # soft delete — 레코드는 감사용으로 남는다.
    await db_session.refresh(row)
    assert bool(row.is_active) is False


def test_deactivate_missing_key_exit3(capsys):
    rc = _run(["deactivate", "--id", "00000000-0000-0000-0000-000000000000"])
    assert rc == 3
    assert "회수 실패" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 목록 · 검증 · 인자 검증
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_does_not_leak_hash_or_plaintext(capsys, db_session: AsyncSession):
    assert await _arun(["issue", "--name", "목록 확인"]) == 0
    raw = capsys.readouterr().out.strip()

    result = await db_session.execute(
        select(IntakeServiceKey).where(IntakeServiceKey.name == "목록 확인")
    )
    row = result.scalar_one()

    assert await _arun(["list"]) == 0
    out = capsys.readouterr()
    listing = out.out + out.err
    assert "목록 확인" in listing
    assert str(row.id) in listing
    assert raw not in listing  # 평문 미노출
    assert str(row.key_hash) not in listing  # 해시 미노출


def test_verify_via_env(capsys, monkeypatch):
    assert _run(["issue", "--name", "검증용"]) == 0
    raw = capsys.readouterr().out.strip()

    monkeypatch.setenv("CLICKEYE_SERVICE_KEY", raw)
    assert _run(["verify"]) == 0
    assert "검증 성공" in capsys.readouterr().err


def test_verify_rejects_unknown_key(capsys, monkeypatch):
    monkeypatch.setenv("CLICKEYE_SERVICE_KEY", "존재하지-않는-평문-키")
    assert _run(["verify"]) == 3
    assert "검증 실패" in capsys.readouterr().err


def test_verify_empty_input_exit2(capsys, monkeypatch):
    monkeypatch.delenv("CLICKEYE_SERVICE_KEY", raising=False)
    assert _run(["verify"]) == 2
    assert "평문이 비어 있습니다" in capsys.readouterr().err


def test_issue_blank_name_exit2(capsys):
    assert _run(["issue", "--name", "   "]) == 2
    assert "--name 이 비어 있습니다" in capsys.readouterr().err


def test_issue_bad_organization_uuid_exit2(capsys):
    assert _run(["issue", "--name", "조직 오류", "--organization", "not-a-uuid"]) == 2
    assert "UUID 형식이 아닙니다" in capsys.readouterr().err


def test_deactivate_bad_uuid_exit2(capsys):
    assert _run(["deactivate", "--id", "nope"]) == 2
    assert "UUID 형식이 아닙니다" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 회귀: 기존 키 인증 경로 불변
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_preexisting_key_still_authenticates(db_session: AsyncSession):
    """CLI 없이 만들어진 기존 키(해시 직접 저장)의 인증이 그대로 동작한다."""
    raw = "legacy-plaintext-key-from-before-cli"
    db_session.add(
        IntakeServiceKey(name="레거시", key_hash=hashlib.sha256(raw.encode()).hexdigest())
    )
    await db_session.commit()

    key = await IntakeService(db_session).authenticate_key(raw)
    assert key.name == "레거시"
