"""Async database setup and session dependency."""

from __future__ import annotations

from contextlib import asynccontextmanager

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Base class for ORM models."""


def _engine_factory() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, echo=False)


ASYNC_ENGINE: AsyncEngine = _engine_factory()

# sessionmaker (SQLAlchemy 2.0 style)
AsyncSessionMaker = async_sessionmaker(ASYNC_ENGINE, expire_on_commit=False)


async def init_db() -> None:  # pragma: no cover
    """Create tables on startup (simple, no migrations)."""
    async with ASYNC_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session."""
    async with AsyncSessionMaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise 