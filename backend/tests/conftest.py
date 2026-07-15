"""Base de donnees jetable, recreee pour chaque test."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base

# Import necessaire pour que Base.metadata connaisse les tables a creer.
from app.models import membership, organization, user  # noqa: F401


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    moteur = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with moteur.begin() as connexion:
        await connexion.run_sync(Base.metadata.create_all)

    fabrique = async_sessionmaker(moteur, expire_on_commit=False)
    async with fabrique() as session:
        yield session

    await moteur.dispose()
