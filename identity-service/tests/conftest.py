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
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db import Base, get_db
from app.models.user_model import User
from app.models.session_model import Session as UserSession
from app.utils.current_user import get_current_user


# -------------------------------------------------------------------
# GLOBAL TEST ENGINE (Async SQLite in-memory or your test PostgreSQL)
# -------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
# If you're using asyncpg for tests:
# TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/test_db"

engine_test = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True,
)

TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine_test,
    expire_on_commit=False,
)


# -------------------------------------------------------------------
# OVERRIDE get_db
# -------------------------------------------------------------------

async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db


# -------------------------------------------------------------------
# DATABASE SETUP + TEARDOWN
# -------------------------------------------------------------------

@pytest.fixture(scope="session")
async def test_engine():
    """Create all tables at the start of the test session."""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine_test
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def db_session(test_engine):
    """
    Creates a clean DB session per test function.
    Automatically rolls back & cleans up after test.
    """
    async with TestingSessionLocal() as session:
        # Clean sessions and users before each test
        await session.execute(delete(UserSession))
        await session.execute(delete(User))
        await session.commit()

        yield session

        await session.rollback()
        await session.close()


# -------------------------------------------------------------------
# ASYNC TEST CLIENT FIXTURE
# -------------------------------------------------------------------

@pytest.fixture
async def async_client():
    """Async httpx client for FastAPI."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


# -------------------------------------------------------------------
# TEST USER FACTORY
# -------------------------------------------------------------------

@pytest.fixture
async def test_user(db_session: AsyncSession):
    """
    Inserts a test user into the database and returns it.
    Matches the expected fields of your real User model.
    """
    new_user = User(
        id=str(uuid.uuid4()),
        email="auth@test.com",
        password="$2b$12$T6uCo0P0RgxNPlZ1htD7zePQWj5nGdI72VrT7x7GgVxS0FvC5bAlu",  # bcrypt for "strongpass123"
        is_active=True,
        is_verified=True,
    )

    db_session.add(new_user)
    await db_session.commit()
    await db_session.refresh(new_user)

    return new_user


# -------------------------------------------------------------------
# OPTIONAL: MOCK CURRENT USER (only if needed)
# -------------------------------------------------------------------

@pytest.fixture
def mock_current_user(monkeypatch, test_user):
    """
    If routes depend on `current_user`, this overrides it with the test user.
    """

    async def fake_current_user():
        return test_user

    monkeypatch.setattr(
        "app.utils.current_user.get_current_user",
        fake_current_user
    )

    return test_user


# -------------------------------------------------------------------
# EVENT LOOP FIX (REQUIRED FOR WINDOWS/WSL)
# -------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for pytest-asyncio on Windows/WSL.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
