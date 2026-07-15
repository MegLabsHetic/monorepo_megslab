"""Le parcours d'inscription/connexion fonctionne de bout en bout via l'API."""

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.main import create_app


async def _client(db: AsyncSession) -> AsyncClient:
    app = create_app()

    async def db_de_test():
        yield db

    app.dependency_overrides[get_db] = db_de_test
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_inscription_puis_connexion_puis_profil(db: AsyncSession) -> None:
    async with await _client(db) as client:
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


async def test_profil_sans_jeton_est_refuse(db: AsyncSession) -> None:
    async with await _client(db) as client:
        reponse = await client.get("/auth/moi")

    assert reponse.status_code == 401
