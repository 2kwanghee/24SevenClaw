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
