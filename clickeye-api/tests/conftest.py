import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.api.v1.prototype_sessions as _proto_router
from app.database import Base, get_db
from app.main import app
from app.models import User  # noqa: F401 — 테이블 등록용
from app.models.pm_profile import PMProfile

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
async def _setup_db(request: pytest.FixtureRequest) -> AsyncIterator[None]:
    """각 테스트 전에 테이블 생성, 후에 삭제.

    백그라운드 태스크가 테스트 DB를 사용하도록 세션 팩토리도 교체한다.
    `no_db` 마커가 있는 테스트(순수 단위 테스트)는 DB 설정을 건너뛴다.
    """
    if request.node.get_closest_marker("no_db"):
        yield
        return

    # 백그라운드 태스크용 세션 팩토리를 테스트 DB로 교체
    original_factory = _proto_router._bg_session_factory
    _proto_router._bg_session_factory = TestSession

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # 세션 팩토리 복원
    _proto_router._bg_session_factory = original_factory


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
async def seeded_pm_profiles(db_session: AsyncSession) -> list[str]:
    """테스트용 PM 프로필 3개를 시딩하고 ID 목록을 반환한다.

    domain: product / backend / growth 각 1개씩 생성.
    """
    profiles = [
        PMProfile(
            id=uuid.uuid4(),
            name="김제품",
            slug="kim-product",
            domain="product",
            title="제품 전략 PM",
            description="제품 전략 전문 PM",
            specialties=["roadmap", "user-research", "a/b-testing"],
            personality={"leadership": 9, "communication": 8},
            is_active=True,
        ),
        PMProfile(
            id=uuid.uuid4(),
            name="이백엔드",
            slug="lee-backend",
            domain="backend",
            title="백엔드 아키텍처 PM",
            description="백엔드 아키텍처 전문 PM",
            specialties=["system-design", "api-design", "database"],
            personality={"technical": 9, "detail-oriented": 8},
            is_active=True,
        ),
        PMProfile(
            id=uuid.uuid4(),
            name="박그로스",
            slug="park-growth",
            domain="growth",
            title="성장 전략 PM",
            description="성장 전략 전문 PM",
            specialties=["analytics", "marketing", "conversion"],
            personality={"data-driven": 9, "creative": 7},
            is_active=True,
        ),
    ]
    for p in profiles:
        db_session.add(p)
    await db_session.commit()

    ids: list[str] = []
    for p in profiles:
        await db_session.refresh(p)
        ids.append(str(p.id))
    return ids


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
