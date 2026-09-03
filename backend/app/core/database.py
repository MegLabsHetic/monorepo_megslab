"""Moteur de base de donnees asynchrone et fabrique de sessions."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Classe de base commune a tous les modeles ORM."""


_engine = create_async_engine(get_settings().database_url)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def creer_session() -> AsyncSession:
    """Une session hors requete HTTP, pour les scripts d'administration."""
    return _session_factory()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependance FastAPI : une session par requete, fermee a la fin."""
    async with _session_factory() as session:
        yield session
