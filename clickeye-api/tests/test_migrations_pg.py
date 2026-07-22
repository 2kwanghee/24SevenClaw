"""실 Postgres 마이그레이션 스모크 테스트 (`@pytest.mark.pg`).

기존 단위 테스트는 SQLite in-memory 에 `Base.metadata.create_all` 로 스키마를
만들기 때문에 alembic 마이그레이션 자체와 PostgreSQL 전용 기능(JSONB 캐스트,
`gen_random_uuid()` 서버 기본값 등)은 검증되지 않는다. 이 테스트는 **빈 실
Postgres** 에 `alembic upgrade head` 를 실제로 적용해, 마이그레이션 체인이
head 까지 예외 없이 올라가고 핵심 테이블이 생성되는지를 검증한다.

TEST_DATABASE_URL(postgresql+asyncpg://...) 미설정 시 conftest 의
`pytest_collection_modifyitems` 가 skip 처리한다. 대상 DB 는 스키마를 초기화
(DROP/CREATE public)하므로 **반드시 폐기 가능한 전용 테스트 DB** 여야 한다.
"""

import os
import subprocess
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

pytestmark = pytest.mark.pg

# clickeye-api 레포 루트 (alembic.ini 위치) — subprocess cwd 로 사용
API_ROOT = Path(__file__).resolve().parents[1]

# head 까지 올라갔을 때 존재해야 하는 핵심 테이블.
# organization_memberships 는 045_org_membership_backfill 대상.
REQUIRED_TABLES = {
    "users",
    "projects",
    "organizations",
    "organization_memberships",
    "alembic_version",
}


async def _reset_public_schema(engine: AsyncEngine) -> None:
    """대상 DB 를 빈 상태로 초기화한다 (from-scratch 마이그레이션 검증용)."""
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))


def _run_alembic(args: list[str], db_url: str) -> subprocess.CompletedProcess[str]:
    """alembic CLI 를 subprocess 로 실행한다.

    alembic/env.py 는 `app.config.settings.database_url`(= DATABASE_URL env) 를
    사용하며 settings 는 import 시점에 고정되는 싱글턴이라, 런타임 URL 주입은
    별도 프로세스(DATABASE_URL env)로 수행해야 한다.
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    return subprocess.run(
        ["alembic", *args],
        cwd=API_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


async def _existing_tables(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        return {row[0] for row in result.fetchall()}


async def test_alembic_upgrade_head_on_fresh_postgres(
    pg_engine: AsyncEngine, pg_database_url: str
) -> None:
    """빈 Postgres 에 alembic upgrade head 가 깨끗이 적용되고 핵심 테이블이 생성된다."""
    # 1. 빈 스키마로 초기화
    await _reset_public_schema(pg_engine)
    tables_before = await _existing_tables(pg_engine)
    assert "users" not in tables_before, "초기화 후 스키마가 비어있어야 한다"

    # 2. head 까지 마이그레이션 적용 — 예외 없이 완료되어야 함
    result = _run_alembic(["upgrade", "head"], pg_database_url)
    assert result.returncode == 0, (
        f"alembic upgrade head 실패 (rc={result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    # 3. 핵심 테이블 존재 확인
    tables_after = await _existing_tables(pg_engine)
    missing = REQUIRED_TABLES - tables_after
    assert not missing, f"head 적용 후 누락된 테이블: {missing}"

    # 4. alembic_version 이 단일 head 로 스탬프되었는지 확인
    async with pg_engine.connect() as conn:
        versions = (await conn.execute(text("SELECT version_num FROM alembic_version"))).fetchall()
    assert len(versions) == 1, f"단일 head 여야 함, 실제: {[v[0] for v in versions]}"


async def test_membership_dedupe_and_unique_active_index(
    pg_engine: AsyncEngine, pg_database_url: str
) -> None:
    """047: 중복 활성 멤버십 dedupe + 부분 유니크 인덱스 강제 (CE-306 항목1).

    046 까지 올린 상태에서 동일 (user_id, organization_id) 활성 멤버십 2건을 삽입한
    뒤 head(047) 로 올리면, dedupe 로 최신 joined_at 1건만 활성으로 남고, 이후
    동일 조합의 활성 멤버십 삽입은 유니크 인덱스에 의해 IntegrityError 로 차단된다.
    """
    from sqlalchemy.exc import IntegrityError

    await _reset_public_schema(pg_engine)

    # 1) 046 까지만 적용 — organization_memberships 테이블은 있으나 유니크 인덱스는 없음
    result = _run_alembic(["upgrade", "046"], pg_database_url)
    assert result.returncode == 0, (
        f"alembic upgrade 046 실패 (rc={result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    keep_id = uuid.uuid4()  # joined_at 이 더 최신 → dedupe 후 살아남아야 함
    drop_id = uuid.uuid4()  # joined_at 이 과거 → 비활성화되어야 함

    # 2) 사용자/조직/중복 활성 멤버십 2건 삽입 (유니크 인덱스 생성 전이므로 성공)
    async with pg_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, display_name) "
                "VALUES (:id, :email, :name)"
            ),
            {"id": user_id, "email": f"{user_id}@t.local", "name": "dedupe-user"},
        )
        await conn.execute(
            text("INSERT INTO organizations (id, company_name) VALUES (:id, :name)"),
            {"id": org_id, "name": "dedupe-org"},
        )
        await conn.execute(
            text(
                "INSERT INTO organization_memberships "
                "(id, user_id, organization_id, org_role, joined_at, is_active) VALUES "
                "(:id, :u, :o, 'org_member', '2026-01-01T00:00:00+00', true)"
            ),
            {"id": drop_id, "u": user_id, "o": org_id},
        )
        await conn.execute(
            text(
                "INSERT INTO organization_memberships "
                "(id, user_id, organization_id, org_role, joined_at, is_active) VALUES "
                "(:id, :u, :o, 'org_member', '2026-06-01T00:00:00+00', true)"
            ),
            {"id": keep_id, "u": user_id, "o": org_id},
        )

    # 3) head(047) 로 — dedupe 실행 + 부분 유니크 인덱스 생성. 예외 없이 완료돼야 함
    result = _run_alembic(["upgrade", "head"], pg_database_url)
    assert result.returncode == 0, (
        f"alembic upgrade head 실패 (rc={result.returncode})\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    async with pg_engine.connect() as conn:
        active_ids = {
            row[0]
            for row in (
                await conn.execute(
                    text(
                        "SELECT id FROM organization_memberships "
                        "WHERE user_id = :u AND organization_id = :o AND is_active IS TRUE"
                    ),
                    {"u": user_id, "o": org_id},
                )
            ).fetchall()
        }
        # 4) 최신 joined_at 1건만 활성으로 남는다
        assert active_ids == {keep_id}, f"dedupe 후 활성은 keep_id 1건이어야 함, 실제: {active_ids}"

        # 5) 부분 유니크 인덱스가 존재한다
        idx = (
            await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename = 'organization_memberships' "
                    "AND indexname = 'uq_org_membership_active'"
                )
            )
        ).fetchall()
        assert len(idx) == 1, "uq_org_membership_active 부분 유니크 인덱스가 존재해야 함"

    # 6) 동일 (user, org) 활성 멤버십 추가 삽입은 유니크 인덱스로 차단된다
    with pytest.raises(IntegrityError):
        async with pg_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO organization_memberships "
                    "(id, user_id, organization_id, org_role, joined_at, is_active) VALUES "
                    "(:id, :u, :o, 'org_member', now(), true)"
                ),
                {"id": uuid.uuid4(), "u": user_id, "o": org_id},
            )
