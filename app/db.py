"""Async SQLAlchemy engine, session factory, and declarative base.

Each request handler acquires its own `AsyncSession` (and thus its own pooled
connection) via the `get_session` dependency. That per-request isolation is what
makes the class-6 credit-decrement race observable across concurrent handlers.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a fresh async session per request."""
    async with SessionLocal() as session:
        yield session
