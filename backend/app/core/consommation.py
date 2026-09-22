"""Ce qu'un appel au modele a consomme, et ce qu'il a coute.

Ces deux objets circulent entre les fournisseurs, les agents et le FinOps. Ils
vivent a part pour que les fournisseurs puissent les rendre sans dependre du
client qui les orchestre.
"""

from dataclasses import dataclass, field
from typing import TypeVar

from pydantic import BaseModel

from app.core.tarifs import ANTHROPIC_OPUS_5, Tarif

Sortie = TypeVar("Sortie", bound=BaseModel)

_MILLION = 1_000_000


@dataclass(frozen=True)
class Consommation:
    """Les jetons d'un appel, et le tarif qui permet de les convertir en cout.

    Le tarif est porte par la consommation, pas deduit apres coup : des lors
    qu'un rabattement peut faire repondre un autre fournisseur, le cout d'un
    appel ne se calcule plus qu'a partir de qui a effectivement repondu.
    """

    jetons_entree: int
    jetons_sortie: int
    jetons_cache_lus: int
    jetons_cache_ecrits: int
    tarif: Tarif = field(default=ANTHROPIC_OPUS_5)

    @property
    def cout_dollars(self) -> float:
        return (
            self.jetons_entree * self.tarif.entree
            + self.jetons_sortie * self.tarif.sortie
            + self.jetons_cache_lus * self.tarif.cache_lecture
            + self.jetons_cache_ecrits * self.tarif.cache_ecriture
        ) / _MILLION

    @property
    def jetons_total(self) -> int:
        return (
            self.jetons_entree
            + self.jetons_sortie
            + self.jetons_cache_lus
            + self.jetons_cache_ecrits
        )


@dataclass(frozen=True)
class Reponse[T: BaseModel]:
    """Une reponse structuree, accompagnee de ce qu'elle a coute."""

    contenu: T
    consommation: Consommation
