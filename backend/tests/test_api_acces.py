"""Les roles sont appliques par l'API : un lecteur lit, un etranger ne voit rien."""

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
from app.models.workspace import Workspace
from app.models.workspace_access import WorkspaceAccess
from app.services.auth_service import ALGORITHME_JWT

CONNEXION = {
    "nom": "Ma base",
    "host": "hote",
    "port": 5432,
    "database": "base",
    "username": "user",
    "mot_de_passe": "mdp",
}


async def _monde(db: AsyncSession) -> dict[str, str]:
    """Acme avec Ada (owner) et Bob (lecteur de l'espace) ; Zoe dans une autre organisation."""
    acme, autre = Organization(nom="Acme"), Organization(nom="Autre")
    ada = User(email="ada@example.com", nom_complet="Ada")
    bob = User(email="bob@example.com", nom_complet="Bob")
    zoe = User(email="zoe@example.com", nom_complet="Zoe")
    db.add_all([acme, autre, ada, bob, zoe])
    await db.flush()
    espace = Workspace(
        id="espace-acme",
        organization_id=acme.id,
        nom="General",
        airbyte_workspace_id="w",
        airbyte_destination_id="d",
        schema_entrepot="ws_acme",
    )
    db.add(espace)
    await db.flush()
    db.add_all(
        [
            Membership(user_id=ada.id, organization_id=acme.id, role=Role.OWNER),
            Membership(user_id=bob.id, organization_id=acme.id, role=Role.MEMBER),
            WorkspaceAccess(user_id=bob.id, workspace_id=espace.id, role=Role.VIEWER),
            Membership(user_id=zoe.id, organization_id=autre.id, role=Role.OWNER),
        ]
    )
    await db.commit()
    return {"ada": ada.id, "bob": bob.id, "zoe": zoe.id}


def _client(db: AsyncSession, airbyte_client: AirbyteClient, user_id: str) -> AsyncClient:
    jeton = jwt.encode({"sub": user_id}, get_settings().jwt_secret, algorithm=ALGORITHME_JWT)
    app = create_app()

    async def db_de_test():
        yield db

    app.dependency_overrides[get_db] = db_de_test
    app.dependency_overrides[get_airbyte_client] = lambda: airbyte_client
    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {jeton}"},
    )


async def test_un_lecteur_lit_mais_ne_connecte_pas(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    ids = await _monde(db)
    async with _client(db, airbyte_client_factice, ids["bob"]) as bob:
        assert (await bob.get("/espaces/espace-acme/sources")).status_code == 200
        espaces = (await bob.get("/espaces")).json()
        assert [(e["id"], e["role"]) for e in espaces] == [("espace-acme", "viewer")]

        refus = await bob.post("/espaces/espace-acme/sources", json=CONNEXION)
        assert refus.status_code == 403
        assert (await bob.post("/espaces", json={"nom": "Perso"})).status_code == 403


async def test_un_proprietaire_herite_de_l_acces_admin_a_chaque_espace(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    ids = await _monde(db)
    async with _client(db, airbyte_client_factice, ids["ada"]) as ada:
        assert (await ada.post("/espaces/espace-acme/sources", json=CONNEXION)).status_code == 201
        cree = await ada.post("/espaces", json={"nom": "Finance"})
        assert cree.status_code == 201 and cree.json()["role"] == "admin"
        assert cree.json()["schema_entrepot"] == f"ws_{cree.json()['id']}"
        # Bob n'a pas d'acces au nouvel espace : pour lui, il n'existe pas.
        async with _client(db, airbyte_client_factice, ids["bob"]) as bob:
            assert (await bob.get(f"/espaces/{cree.json()['id']}")).status_code == 404


async def test_un_etranger_ne_voit_pas_l_espace(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    ids = await _monde(db)
    async with _client(db, airbyte_client_factice, ids["zoe"]) as zoe:
        assert (await zoe.get("/espaces/espace-acme")).status_code == 404
        assert (await zoe.get("/espaces/espace-acme/sources")).status_code == 404
        assert (await zoe.get("/espaces/espace-acme/conversations")).status_code == 404


async def test_l_equipe_est_reservee_aux_admins_de_l_organisation(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    ids = await _monde(db)
    async with _client(db, airbyte_client_factice, ids["bob"]) as bob:
        assert (await bob.get("/organisation/membres")).status_code == 200  # voir l'equipe : oui
        refus = await bob.post(
            "/organisation/invitations", json={"email": "x@example.com", "role": "member"}
        )
        assert refus.status_code == 403
    async with _client(db, airbyte_client_factice, ids["ada"]) as ada:
        invitation = await ada.post(
            "/organisation/invitations",
            json={
                "email": "x@example.com",
                "role": "member",
                "acces": [{"espace_id": "espace-acme", "role": "member"}],
            },
        )
        assert invitation.status_code == 201 and invitation.json()["jeton"]
        profil = await ada.get("/auth/moi")
        assert profil.json()["organisation"]["role"] == "owner"


async def test_la_console_plateforme_est_reservee_au_super_admin(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    ids = await _monde(db)
    async with _client(db, airbyte_client_factice, ids["ada"]) as ada:
        assert (await ada.get("/plateforme/organisations")).status_code == 403
    operateur = await db.get(User, ids["zoe"])
    assert operateur is not None
    operateur.est_super_admin = True
    await db.commit()
    async with _client(db, airbyte_client_factice, ids["zoe"]) as zoe:
        organisations = await zoe.get("/plateforme/organisations")
        assert organisations.status_code == 200
        assert sorted(o["nom"] for o in organisations.json()) == ["Acme", "Autre"]
