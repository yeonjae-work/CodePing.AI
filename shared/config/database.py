"""Database configuration and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from shared.config.settings import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


def get_engine():
    """Get SQLAlchemy engine (sync or async based on database URL)."""
    settings = get_settings()
    
    if settings.database_url.startswith(("sqlite+aiosqlite", "postgresql+asyncpg")):
        return create_async_engine(settings.database_url, echo=False)
    else:
        return create_engine(settings.database_url, echo=False)


def get_session_maker():
    """Get session maker (sync or async based on engine type)."""
    engine = get_engine()
    
    if hasattr(engine, 'sync_engine'):  # async engine
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    else:  # sync engine
        return sessionmaker(bind=engine)


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session context manager."""
    async_session_maker = get_session_maker()
    
    async with async_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    engine = get_engine()
    
    if hasattr(engine, 'sync_engine'):  # async engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:  # sync engine
        Base.metadata.create_all(bind=engine) 