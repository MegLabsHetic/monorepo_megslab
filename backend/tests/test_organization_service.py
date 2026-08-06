"""La creation d'une organisation provisionne un workspace Airbyte et un OWNER."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.core.errors import ErreurUtilisateur
from app.models.membership import Membership, Role
from app.models.user import User
from app.services.organization_service import OrganizationService


async def test_le_createur_devient_owner_de_l_organisation(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    utilisateur = User(email="ada@example.com", nom_complet="Ada")
    db.add(utilisateur)
    await db.flush()

    organisation = await OrganizationService(db, airbyte_client_factice).creer_avec_proprietaire(
        nom="Espace de Ada", proprietaire=utilisateur
    )
    await db.commit()

    assert organisation.airbyte_workspace_id == "workspace-test"

    resultat = await db.execute(
        select(Membership).where(Membership.organization_id == organisation.id)
    )
    membership = resultat.scalar_one()
    assert membership.user_id == utilisateur.id
    assert membership.role == Role.OWNER


async def test_refuse_de_creer_l_organisation_si_airbyte_est_injoignable(
    db: AsyncSession,
) -> None:
    def gestionnaire(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client_en_panne = AirbyteClient(
        "http://airbyte.local",
        "id",
        "secret",
        http=httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire)),
    )
    utilisateur = User(email="ada@example.com", nom_complet="Ada")
    db.add(utilisateur)
    await db.flush()

    with pytest.raises(ErreurUtilisateur):
        await OrganizationService(db, client_en_panne).creer_avec_proprietaire(
            nom="Espace de Ada", proprietaire=utilisateur
        )
