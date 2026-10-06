"""Chiffrement des cles d'API stockees en base.

Une cle de fournisseur posee depuis l'interface ne peut pas dormir en clair
dans la base : une sauvegarde qui fuite, une console d'administration mal
protegee, et c'est la facture d'inference de tout le monde qui part avec.

Le chiffrement est symetrique et la cle vient de l'environnement. Ce n'est
donc pas une protection contre quelqu'un qui a deja le serveur ET le .env :
c'est une protection contre une fuite de la base seule, qui est le scenario
courant.

Consequence a connaitre : changer SECRET_CHIFFREMENT rend illisibles toutes
les cles deja enregistrees. Elles devront etre resaisies, et le code le dit
plutot que de laisser croire a une panne du fournisseur.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur


class SecretIllisible(RuntimeError):
    """Le secret ne peut pas etre dechiffre avec la cle courante."""


def _fernet() -> Fernet:
    reglages = get_settings()
    source = reglages.secret_chiffrement or reglages.jwt_secret
    if not source:
        raise ErreurUtilisateur(
            "Le chiffrement des cles n'est pas configure sur ce serveur.", code_http=503
        )
    # Fernet exige 32 octets en base64url. On derive depuis le secret plutot
    # que d'imposer un format exact dans le .env.
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(source.encode()).digest()))


def chiffrer(valeur: str) -> str:
    return _fernet().encrypt(valeur.encode()).decode()


def dechiffrer(chiffre: str) -> str:
    try:
        return _fernet().decrypt(chiffre.encode()).decode()
    except InvalidToken as erreur:
        raise SecretIllisible(
            "Cette cle a ete chiffree avec un autre SECRET_CHIFFREMENT. "
            "Resaisissez-la depuis l'interface."
        ) from erreur


def masquer(valeur: str) -> str:
    """Ce qu'on rend a l'interface : de quoi reconnaitre la cle, pas de quoi s'en servir."""
    if not valeur:
        return ""
    if len(valeur) <= 8:
        return "*" * len(valeur)
    return f"{valeur[:4]}...{valeur[-4:]}"
