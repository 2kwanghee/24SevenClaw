import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app
from app.models import User  # noqa: F401 — 테이블 등록용

# 테스트용 SQLite in-memory async 엔진
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# SQLite에서 PostgreSQL 함수 호환
@event.listens_for(test_engine.sync_engine, "connect")
def _register_sqlite_functions(dbapi_connection, connection_record):  # type: ignore[no-untyped-def]
    dbapi_connection.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
    dbapi_connection.create_function(
        "now", 0, lambda: datetime.now(UTC).isoformat()
    )


@pytest.fixture(autouse=True)
async def _setup_db() -> AsyncIterator[None]:
    """각 테스트 전에 테이블 생성, 후에 삭제."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """테스트용 async DB 세션."""
    async with TestSession() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """테스트용 HTTP 클라이언트 (DB 세션 오버라이드 포함)."""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """회원가입 후 로그인하여 인증 헤더 반환."""
    # 테스트 유저 등록
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "display_name": "테스트 유저",
        },
    )
    # 로그인
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
