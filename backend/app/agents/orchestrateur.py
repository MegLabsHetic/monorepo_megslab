"""L'Orchestrateur : fait travailler les agents dans l'ordre, et rend compte.

Il ne choisit ni les modeles ni les prompts — ca appartient aux agents et au
client LLM. Il enchaine les etapes, mesure chacune, additionne ce qu'elles ont
coute, et rend un compte-rendu que l'interface peut montrer tel quel : quel
agent a fait quoi, en combien de temps, pour combien.
"""

import time
from dataclasses import dataclass, field

from app.agents.analyste import Analyste, ResultatAnalyse
from app.agents.redacteur import Redacteur
from app.core.duckdb_engine import DuckDBEngine, Resultat
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import Consommation, LLMClient


@dataclass(frozen=True)
class Etape:
    """Une etape du traitement, telle que l'interface la montre."""

    agent: str
    statut: str  # "terminee" | "refusee" | "ignoree"
    duree_ms: int
    detail: str = ""


@dataclass
class ReponseComplete:
    question: str
    reponse: str
    sql: str | None
    resultat: Resultat | None
    etapes: list[Etape] = field(default_factory=list)
    consommations: list[Consommation] = field(default_factory=list)
    duree_ms: int = 0

    @property
    def cout_dollars(self) -> float:
        return sum(c.cout_dollars for c in self.consommations)

    @property
    def jetons(self) -> int:
        return sum(c.jetons_total for c in self.consommations)


class Orchestrateur:
    def __init__(self, moteur: DuckDBEngine, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()
        self._analyste = Analyste(moteur, self._llm)
        self._redacteur = Redacteur(self._llm)

    async def repondre(self, question: str, schema: str) -> ReponseComplete:
        depart = time.perf_counter()
        etapes: list[Etape] = []
        consommations: list[Consommation] = []

        analyse = await self._etape_analyse(question, schema, etapes)
        consommations.extend(analyse.consommations)

        if analyse.resultat is None:
            # L'Analyste a juge la question sans reponse dans ce schema : son
            # explication EST la reponse. Pas de Redacteur, pas de cout en plus.
            etapes.append(Etape("redacteur", "ignoree", 0, "rien a formuler"))
            return ReponseComplete(
                question=question,
                reponse=analyse.plan.explication,
                sql=None,
                resultat=None,
                etapes=etapes,
                consommations=consommations,
                duree_ms=_ms(depart),
            )

        redaction = await self._etape_redaction(question, analyse, etapes)
        consommations.append(redaction.consommation)

        return ReponseComplete(
            question=question,
            reponse=redaction.contenu.reponse,
            sql=analyse.sql_execute,
            resultat=analyse.resultat,
            etapes=etapes,
            consommations=consommations,
            duree_ms=_ms(depart),
        )

    async def _etape_analyse(
        self, question: str, schema: str, etapes: list[Etape]
    ) -> ResultatAnalyse:
        depart = time.perf_counter()
        try:
            analyse = await self._analyste.repondre(question, schema)
        except ErreurUtilisateur as refus:
            etapes.append(Etape("analyste", "refusee", _ms(depart), refus.message))
            raise
        detail = (
            f"{analyse.resultat.nb_lignes} ligne(s)"
            if analyse.resultat is not None
            else "pas de requete possible"
        )
        if analyse.corrigee:
            # Dire qu'il y a eu une reprise fait partie du compte-rendu : elle
            # a coute un appel de plus, et le lecteur doit pouvoir le voir.
            detail += ", apres une correction"
        etapes.append(Etape("analyste", "terminee", _ms(depart), detail))
        return analyse

    async def _etape_redaction(self, question: str, analyse: ResultatAnalyse, etapes: list[Etape]):
        depart = time.perf_counter()
        assert analyse.sql_execute is not None and analyse.resultat is not None
        redaction = await self._redacteur.rediger(question, analyse.sql_execute, analyse.resultat)
        etapes.append(Etape("redacteur", "terminee", _ms(depart)))
        return redaction


def _ms(depart: float) -> int:
    return int((time.perf_counter() - depart) * 1000)
