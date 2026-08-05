"""Inscription, connexion et emission des jetons de session."""

from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur
from app.models.user import User
from app.services.organization_service import OrganizationService

_hacheur = PasswordHasher()
ALGORITHME_JWT = "HS256"
DUREE_SESSION = timedelta(hours=12)


class AuthService:
    """Une methode = une etape du parcours d'authentification."""

    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient | None = None) -> None:
        self._db = db
        self._airbyte_client = airbyte_client or get_airbyte_client()

    async def inscrire(self, email: str, mot_de_passe: str, nom_complet: str) -> User:
        """Cree un compte et son organisation par defaut, dans une seule transaction.

        Un utilisateur sans organisation ne peut rien faire d'utile dans MegLabs
        (aucune source de donnees n'existe hors d'une organisation) : les deux
        naissent ensemble, ou ni l'un ni l'autre. Si le workspace Airbyte ne
        peut pas etre cree, on annule tout plutot que de laisser un compte a
        moitie forme.
        """
        existant = await self._trouver_par_email(email)
        if existant is not None:
            raise ErreurUtilisateur("Un compte existe deja avec cet email.", code_http=409)

        utilisateur = User(
            email=email,
            mot_de_passe_hache=_hacheur.hash(mot_de_passe),
            nom_complet=nom_complet,
        )
        self._db.add(utilisateur)
        await self._db.flush()  # attribue l'id de l'utilisateur sans cloturer la transaction

        try:
            await OrganizationService(self._db, self._airbyte_client).creer_avec_proprietaire(
                nom=f"Espace de {nom_complet}", proprietaire=utilisateur
            )
        except Exception:
            await self._db.rollback()
            raise

        await self._db.commit()
        await self._db.refresh(utilisateur)
        return utilisateur

    async def connecter(self, email: str, mot_de_passe: str) -> str:
        """Verifie les identifiants et renvoie un jeton de session signe."""
        utilisateur = await self._trouver_par_email(email)
        if utilisateur is None or utilisateur.mot_de_passe_hache is None:
            raise ErreurUtilisateur("Email ou mot de passe incorrect.", code_http=401)

        if not self._mot_de_passe_valide(utilisateur.mot_de_passe_hache, mot_de_passe):
            raise ErreurUtilisateur("Email ou mot de passe incorrect.", code_http=401)

        return self._emettre_jeton(utilisateur)

    def _mot_de_passe_valide(self, hache: str, mot_de_passe: str) -> bool:
        try:
            return _hacheur.verify(hache, mot_de_passe)
        except VerifyMismatchError:
            return False

    def _emettre_jeton(self, utilisateur: User) -> str:
        maintenant = datetime.now(UTC)
        charge = {
            "sub": utilisateur.id,
            "iat": maintenant,
            "exp": maintenant + DUREE_SESSION,
        }
        return jwt.encode(charge, get_settings().jwt_secret, algorithm=ALGORITHME_JWT)

    async def _trouver_par_email(self, email: str) -> User | None:
        resultat = await self._db.execute(select(User).where(User.email == email))
        return resultat.scalar_one_or_none()
