"""Dependances FastAPI partagees entre les routes."""

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User
from app.services.auth_service import ALGORITHME_JWT


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
    """L'organisation de l'utilisateur.

    Simplification assumee : un utilisateur n'a qu'une organisation pour
    l'instant (celle creee a l'inscription), donc on prend la premiere. A
    remplacer par un vrai choix quand l'appartenance a plusieurs organisations
    sera geree cote interface.
    """
    resultat = await db.execute(
        select(Organization)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == utilisateur.id)
        .limit(1)
    )
    organisation = resultat.scalar_one_or_none()
    if organisation is None:
        raise ErreurUtilisateur("Aucune organisation associee a ce compte.", code_http=404)
    return organisation
