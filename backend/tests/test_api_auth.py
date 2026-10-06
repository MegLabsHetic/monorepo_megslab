"""Le parcours d'inscription/connexion fonctionne de bout en bout via l'API."""

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.database import get_db
from app.main import create_app


async def _client(db: AsyncSession, airbyte_client: AirbyteClient) -> AsyncClient:
    app = create_app()

    async def db_de_test():
        yield db

    app.dependency_overrides[get_db] = db_de_test
    app.dependency_overrides[get_airbyte_client] = lambda: airbyte_client
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_inscription_puis_connexion_puis_profil(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    async with await _client(db, airbyte_client_factice) as client:
        reponse_inscription = await client.post(
            "/auth/inscription",
            json={
                "email": "ada@example.com",
                "mot_de_passe": "mot-de-passe-solide",
                "nom_complet": "Ada",
            },
        )
        assert reponse_inscription.status_code == 201

        reponse_connexion = await client.post(
            "/auth/connexion",
            json={"email": "ada@example.com", "mot_de_passe": "mot-de-passe-solide"},
        )
        assert reponse_connexion.status_code == 200
        jeton = reponse_connexion.json()["jeton"]

        reponse_profil = await client.get("/auth/moi", headers={"Authorization": f"Bearer {jeton}"})
        assert reponse_profil.status_code == 200
        assert reponse_profil.json()["email"] == "ada@example.com"


async def test_profil_sans_jeton_est_refuse(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    async with await _client(db, airbyte_client_factice) as client:
        reponse = await client.get("/auth/moi")

    assert reponse.status_code == 401
