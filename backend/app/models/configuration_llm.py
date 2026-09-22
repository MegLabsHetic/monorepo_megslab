"""La configuration des modeles, modifiable sans redeployer.

Jusqu'ici la chaine de fournisseurs vivait dans le fichier d'environnement : la
changer supposait un deploiement. C'est sur pour la production, et impraticable
pour essayer un fournisseur un mardi soir.

Ces deux lignes coexistent desormais, avec une regle claire : **ce qui est en
base l'emporte, et ce qui est vide retombe sur l'environnement.** On peut donc
poser une chaine depuis l'interface, la retirer, et retrouver exactement le
comportement precedent.

Les cles d'API sont chiffrees (voir `secrets_chiffres`) et ne ressortent jamais
de l'API : l'interface n'en recoit qu'une empreinte masquee.
"""

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import HorodatageMixin

AGENTS = ("analyste", "redacteur", "viz")
FOURNISSEURS = ("anthropic", "ovhcloud", "scaleway", "ionos")


class ReglageLLM(HorodatageMixin, Base):
    """Une valeur de configuration, sous une cle libre.

    Table a une seule dimension plutot qu'une colonne par reglage : ajouter un
    fournisseur ou un agent ne doit pas demander une migration.
    """

    __tablename__ = "reglages_llm"

    # « chaine:analyste », « cle:ovhcloud », « ordonnanceur »...
    cle: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    valeur: Mapped[str] = mapped_column(Text, default="", server_default="")
    # Vrai quand `valeur` est chiffree et ne doit jamais sortir en clair.
    secret: Mapped[bool] = mapped_column(Boolean, default=False)


def cle_chaine(agent: str) -> str:
    return f"chaine:{agent}"


def cle_api(fournisseur: str) -> str:
    return f"cle:{fournisseur}"
