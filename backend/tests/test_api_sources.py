"""Le parcours connecter -> synchroniser -> suivre le statut fonctionne via l'API."""

import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.config import get_settings
from app.core.database import get_db
from app.main import create_app
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User
from app.services.auth_service import ALGORITHME_JWT


async def _client_authentifie(db: AsyncSession, airbyte_client: AirbyteClient) -> AsyncClient:
    utilisateur = User(email="ada@example.com", nom_complet="Ada")
    organisation = Organization(
        nom="Espace de Ada",
        airbyte_workspace_id="workspace-test",
        airbyte_destination_id="destination-test",
    )
    db.add_all([utilisateur, organisation])
    await db.flush()
    db.add(Membership(user_id=utilisateur.id, organization_id=organisation.id, role=Role.OWNER))
    await db.commit()

    jeton = jwt.encode({"sub": utilisateur.id}, get_settings().jwt_secret, algorithm=ALGORITHME_JWT)

    app = create_app()

    async def db_de_test():
        yield db

    app.dependency_overrides[get_db] = db_de_test
    app.dependency_overrides[get_airbyte_client] = lambda: airbyte_client
    transport = ASGITransport(app=app)
    return AsyncClient(
        transport=transport, base_url="http://test", headers={"Authorization": f"Bearer {jeton}"}
    )


async def test_connecter_puis_synchroniser_puis_suivre_le_statut(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    async with await _client_authentifie(db, airbyte_client_factice) as client:
        reponse_connexion = await client.post(
            "/sources",
            json={
                "nom": "Ma base",
                "host": "hote",
                "port": 5432,
                "database": "base",
                "username": "user",
                "mot_de_passe": "mdp",
            },
        )
        assert reponse_connexion.status_code == 201
        corps = reponse_connexion.json()
        assert corps["statut"] == "connectee"
        assert corps["flux_disponibles"] == [
            {"nom": "customers", "namespace": "public", "colonnes": []}
        ]

        reponse_sync = await client.post(
            f"/sources/{corps['id']}/synchroniser", json={"flux": ["customers"]}
        )
        assert reponse_sync.status_code == 200
        job_id = reponse_sync.json()["job_id"]

        reponse_statut = await client.get(f"/sources/{corps['id']}/synchronisation/{job_id}")
        assert reponse_statut.status_code == 200
        assert reponse_statut.json()["statut"] == "succeeded"
