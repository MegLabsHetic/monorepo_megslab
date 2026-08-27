"""Base de donnees jetable et client Airbyte factice, recrees pour chaque test."""

from collections.abc import AsyncGenerator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agents.data import AgentData
from app.core.airbyte_client import AirbyteClient
from app.core.database import Base

# Import necessaire pour que Base.metadata connaisse les tables a creer.
from app.models import (  # noqa: F401
    conversation,
    data_source,
    invitation,
    membership,
    organization,
    question,
    user,
    workspace,
    workspace_access,
)


@pytest.fixture(autouse=True)
def _contexte_donnees_oublie():
    """Le cache de l'agent Data est global au processus : chaque test repart a vide."""
    AgentData.oublier_tout()
    yield
    AgentData.oublier_tout()


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
    """Repond avec succes a n'importe quel appel Airbyte, sans jamais toucher le reseau."""

    def gestionnaire(requete: httpx.Request) -> httpx.Response:
        chemin = requete.url.path
        if chemin.endswith("/applications/token"):
            return httpx.Response(200, json={"access_token": "jeton-test", "expires_in": 3600})
        if chemin.endswith("/workspaces"):
            return httpx.Response(200, json={"workspaceId": "workspace-test"})
        if chemin.endswith("/destinations"):
            return httpx.Response(200, json={"destinationId": "destination-test"})
        if chemin.endswith("/sources"):
            return httpx.Response(200, json={"sourceId": "source-test"})
        if "/connections" in chemin:
            return httpx.Response(200, json={"connectionId": "connexion-test"})
        if "/jobs" in chemin:
            return httpx.Response(200, json={"jobId": 1, "status": "succeeded", "rowsSynced": 0})
        if "/streams" in chemin:
            return httpx.Response(
                200,
                json=[
                    {"streamName": "customers", "streamnamespace": "public", "propertyFields": []}
                ],
            )
        return httpx.Response(200, json={})

    http = httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire))
    return AirbyteClient("http://airbyte.local", "id", "secret", http=http)
