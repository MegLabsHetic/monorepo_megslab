"""Base de donnees jetable et client Airbyte factice, recrees pour chaque test."""

from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.airbyte_client import AirbyteClient
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


@pytest.fixture
def airbyte_client_factice() -> AirbyteClient:
    """Repond avec succes a l'authentification et a la creation de workspace."""

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        if requete.url.path.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "jeton-test", "expires_in": 3600})
        return httpx.Response(200, json={"workspaceId": "workspace-test"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire))
    return AirbyteClient("http://airbyte.local", "id", "secret", http=http)
