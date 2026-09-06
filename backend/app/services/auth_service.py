"""Inscription, connexion, emission des jetons de session, profil."""

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
LONGUEUR_MOT_DE_PASSE_MIN = 8


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hacheur.hash(mot_de_passe)


class AuthService:
    """Une methode = une etape du parcours d'authentification."""

    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient | None = None) -> None:
        self._db = db
        self._airbyte_client = airbyte_client or get_airbyte_client()

    async def inscrire(self, email: str, mot_de_passe: str, nom_complet: str) -> User:
        """Cree un compte, son organisation et son premier espace, dans une seule
        transaction.

        Un utilisateur sans espace ne peut rien faire d'utile dans MegsLab
        (aucune source n'existe hors d'un espace) : tout nait ensemble, ou rien.
        Si Airbyte ne repond pas, on annule tout plutot que de laisser un compte
        a moitie forme.
        """
        existant = await self._trouver_par_email(email)
        if existant is not None:
            raise ErreurUtilisateur("Un compte existe deja avec cet email.", code_http=409)

        utilisateur = User(
            email=email.strip().lower(),
            mot_de_passe_hache=hacher_mot_de_passe(mot_de_passe),
            nom_complet=nom_complet.strip(),
        )
        self._db.add(utilisateur)
        await self._db.flush()  # attribue l'id de l'utilisateur sans cloturer la transaction

        try:
            await OrganizationService(self._db, self._airbyte_client).creer_avec_proprietaire(
                nom=f"Organisation de {utilisateur.nom_complet}", proprietaire=utilisateur
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
        if utilisateur is None or utilisateur.mot_de_passe_hache is None or not utilisateur.actif:
            raise ErreurUtilisateur("Email ou mot de passe incorrect.", code_http=401)

        if not self._mot_de_passe_valide(utilisateur.mot_de_passe_hache, mot_de_passe):
            raise ErreurUtilisateur("Email ou mot de passe incorrect.", code_http=401)

        return self.emettre_jeton(utilisateur)

    async def modifier_profil(self, utilisateur: User, nom_complet: str) -> User:
        if not nom_complet.strip():
            raise ErreurUtilisateur("Le nom ne peut pas etre vide.", code_http=422)
        utilisateur.nom_complet = nom_complet.strip()
        await self._db.commit()
        await self._db.refresh(utilisateur)
        return utilisateur

    async def changer_mot_de_passe(self, utilisateur: User, actuel: str, nouveau: str) -> None:
        """Le mot de passe actuel est exige, meme temporaire : c'est ce qui
        prouve que la personne au clavier est bien celle qui s'est connectee."""
        if utilisateur.mot_de_passe_hache is None or not self._mot_de_passe_valide(
            utilisateur.mot_de_passe_hache, actuel
        ):
            raise ErreurUtilisateur("Le mot de passe actuel est incorrect.", code_http=401)
        if len(nouveau) < LONGUEUR_MOT_DE_PASSE_MIN:
            raise ErreurUtilisateur(
                f"Le nouveau mot de passe doit faire au moins {LONGUEUR_MOT_DE_PASSE_MIN} "
                "caracteres.",
                code_http=422,
            )
        if nouveau == actuel:
            raise ErreurUtilisateur("Le nouveau mot de passe doit etre different.", code_http=422)
        utilisateur.mot_de_passe_hache = hacher_mot_de_passe(nouveau)
        utilisateur.doit_changer_mot_de_passe = False
        await self._db.commit()

    def emettre_jeton(self, utilisateur: User) -> str:
        maintenant = datetime.now(UTC)
        charge = {
            "sub": utilisateur.id,
            "iat": maintenant,
            "exp": maintenant + DUREE_SESSION,
        }
        return jwt.encode(charge, get_settings().jwt_secret, algorithm=ALGORITHME_JWT)

    def _mot_de_passe_valide(self, hache: str, mot_de_passe: str) -> bool:
        try:
            return _hacheur.verify(hache, mot_de_passe)
        except VerifyMismatchError:
            return False

    async def _trouver_par_email(self, email: str) -> User | None:
        resultat = await self._db.execute(select(User).where(User.email == email.strip().lower()))
        return resultat.scalar_one_or_none()
