"""Le service d'auth protege le mot de passe et refuse les identifiants invalides."""

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur
from app.services.auth_service import AuthService


async def test_le_mot_de_passe_en_clair_n_est_jamais_stocke(db: AsyncSession) -> None:
    service = AuthService(db)
    utilisateur = await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    assert utilisateur.mot_de_passe_hache != "mot-de-passe-solide"


async def test_un_email_deja_utilise_est_refuse(db: AsyncSession) -> None:
    service = AuthService(db)
    await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    with pytest.raises(ErreurUtilisateur):
        await service.inscrire("ada@example.com", "autre-mot-de-passe", "Ada bis")


async def test_la_connexion_avec_le_bon_mot_de_passe_rend_un_jeton_valide(
    db: AsyncSession,
) -> None:
    service = AuthService(db)
    utilisateur = await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    jeton = await service.connecter("ada@example.com", "mot-de-passe-solide")
    charge = jwt.decode(jeton, get_settings().jwt_secret, algorithms=["HS256"])

    assert charge["sub"] == utilisateur.id


async def test_la_connexion_avec_un_mauvais_mot_de_passe_est_refusee(db: AsyncSession) -> None:
    service = AuthService(db)
    await service.inscrire("ada@example.com", "mot-de-passe-solide", "Ada")

    with pytest.raises(ErreurUtilisateur):
        await service.connecter("ada@example.com", "mauvais-mot-de-passe")


async def test_la_connexion_avec_un_email_inconnu_est_refusee(db: AsyncSession) -> None:
    service = AuthService(db)

    with pytest.raises(ErreurUtilisateur):
        await service.connecter("personne@example.com", "peu-importe")
