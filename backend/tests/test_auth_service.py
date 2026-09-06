"""Le service d'auth protege le mot de passe et refuse les identifiants invalides."""

import httpx
import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur
from app.models.membership import Membership, Role
from app.models.user import User
from app.services.auth_service import AuthService


async def test_le_mot_de_passe_en_clair_n_est_jamais_stocke(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    service = AuthService(db, airbyte_client_factice)
    utilisateur = await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    assert utilisateur.mot_de_passe_hache != "mot-de-passe-solide"


async def test_l_inscription_cree_une_organisation_dont_l_utilisateur_est_owner(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    service = AuthService(db, airbyte_client_factice)
    utilisateur = await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    resultat = await db.execute(select(Membership).where(Membership.user_id == utilisateur.id))
    membership = resultat.scalar_one()
    assert membership.role == Role.OWNER


async def test_un_email_deja_utilise_est_refuse(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    service = AuthService(db, airbyte_client_factice)
    await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    with pytest.raises(ErreurUtilisateur):
        await service.inscrire("ada@example.com", "autre-mot-de-passe", "Ada bis")


async def test_l_inscription_echoue_et_ne_persiste_rien_si_airbyte_est_injoignable(
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
    service = AuthService(db, client_en_panne)

    with pytest.raises(ErreurUtilisateur):
        await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    resultat = await db.execute(select(User).where(User.email == "ada@example.com"))
    assert resultat.scalar_one_or_none() is None


async def test_la_connexion_avec_le_bon_mot_de_passe_rend_un_jeton_valide(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    service = AuthService(db, airbyte_client_factice)
    utilisateur = await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    jeton = await service.connecter("ada@example.com", "mot-de-passe-solide")
    charge = jwt.decode(jeton, get_settings().jwt_secret, algorithms=["HS256"])

    assert charge["sub"] == utilisateur.id


async def test_la_connexion_avec_un_mauvais_mot_de_passe_est_refusee(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    service = AuthService(db, airbyte_client_factice)
    await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    with pytest.raises(ErreurUtilisateur):
        await service.connecter("ada@example.com", "mauvais-mot-de-passe")


async def test_la_connexion_avec_un_email_inconnu_est_refusee(db: AsyncSession) -> None:
    service = AuthService(db)

    with pytest.raises(ErreurUtilisateur):
        await service.connecter("personne@example.com", "peu-importe")


async def test_une_empreinte_de_mot_de_passe_illisible_est_un_refus_pas_une_panne(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    """Une empreinte corrompue en base doit se comporter comme un mauvais mot de
    passe. Laisser remonter l'erreur d'argon2 donnerait une 500, qui apprend a
    qui la provoque que ce compte-la existe."""
    service = AuthService(db, airbyte_client_factice)
    utilisateur = await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")
    utilisateur.mot_de_passe_hache = "ceci-n-est-pas-une-empreinte-argon2"
    await db.commit()

    with pytest.raises(ErreurUtilisateur) as refus:
        await service.connecter("ada@example.com", "mot-de-passe-solide")

    assert refus.value.code_http == 401
