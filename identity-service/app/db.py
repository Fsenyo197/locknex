from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.orm import declarative_base
from app.config import settings
import asyncio

Base = declarative_base()

# Module-level lazy-initialized references
_async_engine: Optional[AsyncEngine] = None
_async_sessionmaker: Optional[async_sessionmaker] = None
_engine_lock = asyncio.Lock()

async def _init_engine_and_sessionmaker() -> None:
    global _async_engine, _async_sessionmaker
    if _async_engine is None:
        # Protect against race condition when called concurrently
        async with _engine_lock:
            if _async_engine is None:
                if not settings.DATABASE_URL:
                    raise RuntimeError(
                        "DATABASE_URL is not set. Set it in your environment or .env"
                    )
                _async_engine = create_async_engine(
                    settings.DATABASE_URL, future=True, echo=False, pool_pre_ping=True
                )
                _async_sessionmaker = async_sessionmaker(
                    bind=_async_engine, class_=AsyncSession, expire_on_commit=False
                )

async def get_engine() -> AsyncEngine:
    await _init_engine_and_sessionmaker()
    assert _async_engine is not None
    return _async_engine

async def get_sessionmaker() -> async_sessionmaker:
    await _init_engine_and_sessionmaker()
    assert _async_sessionmaker is not None
    return _async_sessionmaker

# FastAPI dependency: yields a fresh AsyncSession
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    sm = await get_sessionmaker()
    async with sm() as session:
        yield session

# helper for tests/cli: create/drop tables (runs sync call in async context)
async def create_all():
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_all():
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# for graceful shutdown if you need it
async def dispose_engine():
    global _async_engine
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
