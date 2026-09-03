"""Dependances FastAPI partagees entre les routes : qui est la, et ce qu'il peut faire.

Toute route qui touche un espace passe par `acces_courant` : l'espace vient du
chemin, le role de `AccesService`. Un espace auquel on n'a pas acces est
« introuvable », pas « interdit » : on ne revele pas ce qui existe.
"""

from dataclasses import dataclass

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.membership import Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.services.acces_service import AccesService
from app.services.auth_service import ALGORITHME_JWT


@dataclass(frozen=True)
class AccesEspace:
    """Un espace ouvert par l'utilisateur courant, avec le role qu'il y tient."""

    espace: Workspace
    role: Role
    organisation: Organization


async def utilisateur_courant(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode le jeton porte dans l'en-tete Authorization et charge l'utilisateur."""
    jeton = _extraire_jeton(authorization)
    try:
        charge = jwt.decode(jeton, get_settings().jwt_secret, algorithms=[ALGORITHME_JWT])
    except jwt.PyJWTError as invalide:
        raise ErreurUtilisateur("Session invalide ou expiree.", code_http=401) from invalide

    utilisateur = await db.get(User, charge["sub"])
    if utilisateur is None or not utilisateur.actif:
        raise ErreurUtilisateur("Session invalide ou expiree.", code_http=401)
    return utilisateur


def _extraire_jeton(authorization: str | None) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise ErreurUtilisateur("Authentification requise.", code_http=401)
    return authorization.removeprefix("Bearer ")


async def organisation_courante(
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    organisation = await AccesService(db).organisation_de(utilisateur)
    if organisation is None:
        raise ErreurUtilisateur("Aucune organisation associee a ce compte.", code_http=404)
    return organisation


async def organisation_administree(
    utilisateur: User = Depends(utilisateur_courant),
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """L'organisation, pour une action reservee a ses proprietaires et admins."""
    if not await AccesService(db).est_admin_organisation(utilisateur, organisation):
        raise ErreurUtilisateur(
            "Cette action est reservee aux administrateurs de l'organisation.", code_http=403
        )
    return organisation


async def acces_courant(
    espace_id: str,
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
) -> AccesEspace:
    espace = await db.get(Workspace, espace_id)
    role = await AccesService(db).role_espace(utilisateur, espace) if espace else None
    if espace is None or role is None:
        raise ErreurUtilisateur("Espace introuvable.", code_http=404)
    organisation = await db.get(Organization, espace.organization_id)
    assert organisation is not None
    return AccesEspace(espace=espace, role=role, organisation=organisation)


async def acces_analyste(acces: AccesEspace = Depends(acces_courant)) -> AccesEspace:
    """Tout ce qui interroge ou modifie les donnees : pas pour un lecteur."""
    if acces.role == Role.VIEWER:
        raise ErreurUtilisateur(
            "Votre role de lecteur dans cet espace ne permet pas cette action.", code_http=403
        )
    return acces


async def acces_admin_espace(acces: AccesEspace = Depends(acces_courant)) -> AccesEspace:
    if acces.role != Role.ADMIN:
        raise ErreurUtilisateur(
            "Cette action est reservee aux administrateurs de l'espace.", code_http=403
        )
    return acces


async def super_admin(utilisateur: User = Depends(utilisateur_courant)) -> User:
    if not utilisateur.est_super_admin:
        raise ErreurUtilisateur("Console reservee a l'operateur de la plateforme.", code_http=403)
    return utilisateur
