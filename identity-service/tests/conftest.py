import asyncio
import uuid
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy import delete
from app.main import app
from app.db import Base, get_db
from app.models.user_model import User, UserStatus
from app.models.session_model import Session as UserSession
from app.utils.current_user import get_current_user


# =====================================================================
# TEST DATABASE CONFIGURATION
# =====================================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    bind=engine_test,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# =====================================================================
# OVERRIDE get_db FOR TESTING
# =====================================================================

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db


# =====================================================================
# CREATE/DROP TABLES ONCE PER TEST SESSION
# =====================================================================

@pytest.fixture(scope="session")
async def test_engine():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine_test

    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# =====================================================================
# DB SESSION FIXTURE – CLEAN FOR EACH TEST
# =====================================================================

@pytest.fixture(scope="function")
async def db_session(test_engine):
    async with TestingSessionLocal() as session:

        # CLEAN TABLES BEFORE EACH TEST
        await session.execute(delete(UserSession))
        await session.execute(delete(User))
        await session.commit()

        yield session

        await session.rollback()


# =====================================================================
# ASYNC HTTP CLIENT
# =====================================================================

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as client:
        yield client


# =====================================================================
# TEST USER FIXTURE
# =====================================================================

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """
    Creates a real user in the DB.
    """
    user = User(
        id=uuid.uuid4(),
        email="auth@test.com",
        username="testuser",
        phone_number="123456789",
        hashed_password="$2b$12$T6uCo0P0RgxNPlZ1htD7zePQWj5nGdI72VrT7x7GgVxS0FvC5bAlu",
        is_verified=False,
        status=UserStatus.PENDING_KYC,
        twofa_secret=None,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# =====================================================================
# AUTHENTICATION OVERRIDE FOR API TESTS
# =====================================================================

@pytest.fixture
async def auth_override(test_user):
    """
    Proper FastAPI dependency override for API endpoints that require authentication.
    """
    async def fake_user():
        return test_user

    app.dependency_overrides[get_current_user] = fake_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# =====================================================================
# EVENT LOOP FOR ASYNC TESTS
# =====================================================================

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
