"""Database configuration and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

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


def get_sync_engine():
    """Get synchronous SQLAlchemy engine."""
    settings = get_settings()
    # 동기 버전의 데이터베이스 URL 사용
    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "+psycopg2")
    return create_engine(sync_url, echo=False)


def get_session_maker():
    """Get session maker (sync or async based on engine type)."""
    engine = get_engine()
    
    if hasattr(engine, 'sync_engine'):  # async engine
        return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    else:  # sync engine
        return sessionmaker(bind=engine)


def get_sync_session_maker():
    """Get synchronous session maker."""
    engine = get_sync_engine()
    return sessionmaker(bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get synchronous database session context manager."""
    session_maker = get_sync_session_maker()
    session = session_maker()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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


def create_tables_sync():
    """Create all database tables synchronously."""
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine) 