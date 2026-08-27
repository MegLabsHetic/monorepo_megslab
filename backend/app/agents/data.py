"""L'agent Data : decrit l'entrepot a ceux qui vont l'interroger.

Il n'appelle jamais de modele, par design : ce qu'il produit est lu dans
l'entrepot, et c'est exactement ce qui part ensuite a l'Analyste. Il n'y a
donc rien a deviner ni a verifier — l'interface peut montrer ce texte tel quel.

Le profil coute plusieurs secondes (une ouverture d'entrepot, une requete par
table, une par colonne categorielle). Il est garde en memoire un quart d'heure
et oublie des qu'une synchronisation ou un import modifie l'entrepot.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, replace

from app.core.duckdb_engine import ColonneProfil, DuckDBEngine, TableProfil

DUREE_CACHE_SECONDES = 15 * 60
# En dessous, le taux de vides n'apprend rien au modele ; au-dessus, il change
# la maniere d'ecrire la requete (filtrer les nuls, ou les compter).
SEUIL_VIDES_SIGNALE = 5.0


@dataclass(frozen=True)
class ContexteDonnees:
    tables: tuple[TableProfil, ...]
    depuis_cache: bool = False

    @property
    def est_vide(self) -> bool:
        return not self.tables

    @property
    def nb_tables(self) -> int:
        return len(self.tables)

    @property
    def nb_colonnes(self) -> int:
        return sum(len(table.colonnes) for table in self.tables)

    @property
    def nb_lignes(self) -> int:
        return sum(table.nb_lignes for table in self.tables)

    def resume(self) -> str:
        return (
            f"{self.nb_tables} table(s), {self.nb_colonnes} colonne(s), "
            f"{_nombre(self.nb_lignes)} ligne(s)"
        )

    def texte(self) -> str:
        """Le schema tel qu'il part au modele : noms, types, effectifs, modalites."""
        return "\n".join(_decrire_table(table) for table in self.tables)


_CACHE: dict[str, tuple[float, ContexteDonnees]] = {}


class AgentData:
    def __init__(self, moteur: DuckDBEngine, horloge: Callable[[], float] = time.monotonic) -> None:
        self._moteur = moteur
        self._horloge = horloge

    def decrire(self) -> ContexteDonnees:
        """Le contexte de l'entrepot, relu si celui en memoire est trop vieux."""
        cle = self._moteur.schema_entrepot
        en_cache = _CACHE.get(cle)
        if en_cache and self._horloge() - en_cache[0] < DUREE_CACHE_SECONDES:
            return replace(en_cache[1], depuis_cache=True)

        contexte = ContexteDonnees(tables=tuple(self._moteur.profil_complet()))
        _CACHE[cle] = (self._horloge(), contexte)
        return contexte

    @staticmethod
    def oublier(schema_entrepot: str) -> None:
        """A appeler des que l'entrepot change : le prochain appel relira."""
        _CACHE.pop(schema_entrepot, None)

    @staticmethod
    def oublier_tout() -> None:
        _CACHE.clear()


def _decrire_table(table: TableProfil) -> str:
    entete = f'- entrepot."{table.nom}" ({_nombre(table.nb_lignes)} lignes)'
    colonnes = "\n".join(f"    {_decrire_colonne(colonne)}" for colonne in table.colonnes)
    return f"{entete}\n{colonnes}" if colonnes else entete


def _decrire_colonne(colonne: ColonneProfil) -> str:
    precisions = []
    if colonne.modalites:
        precisions.append("modalites : " + ", ".join(colonne.modalites))
    if colonne.pourcentage_nuls >= SEUIL_VIDES_SIGNALE:
        precisions.append(f"{colonne.pourcentage_nuls:.0f} % de vides")
    base = f"{colonne.nom} {colonne.type}"
    return f"{base} — {' ; '.join(precisions)}" if precisions else base


def _nombre(valeur: int) -> str:
    return f"{valeur:,}".replace(",", " ")
