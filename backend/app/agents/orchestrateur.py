"""L'Orchestrateur : fait travailler les agents dans l'ordre, et rend compte.

Il ne choisit ni les modeles ni les prompts — ca appartient aux agents et au
client LLM. Il enchaine les etapes, mesure chacune, additionne ce qu'elles ont
coute, et rend un compte-rendu que l'interface peut montrer tel quel : quel
agent a fait quoi, en combien de temps, pour combien.

L'ordre : Data decrit l'entrepot, l'Analyste ecrit et execute la requete, ML
lit le resultat comme une serie, puis le Redacteur et Viz travaillent en meme
temps — ils ne dependent que du resultat, pas l'un de l'autre.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field

from app.agents.analyste import Analyste, Echange, ResultatAnalyse
from app.agents.data import AgentData, ContexteDonnees
from app.agents.ml import AgentML, AnalyseSerie
from app.agents.redacteur import Redacteur, Redaction
from app.agents.viz import AgentViz, SpecGraphique
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete, Resultat
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import Consommation, LLMClient, Reponse

logger = logging.getLogger(__name__)


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
    analyse: AnalyseSerie | None = None
    graphique: SpecGraphique | None = None
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
        self._data = AgentData(moteur)
        self._analyste = Analyste(moteur, self._llm)
        self._ml = AgentML()
        self._redacteur = Redacteur(self._llm)
        self._viz = AgentViz(self._llm)

    async def repondre(
        self, question: str, historique: list[Echange] | tuple[Echange, ...] = ()
    ) -> ReponseComplete:
        depart = time.perf_counter()
        etapes: list[Etape] = []
        consommations: list[Consommation] = []

        contexte = await self._etape_data(etapes)
        analyse = await self._etape_analyse(question, contexte.texte(), etapes, historique)
        consommations.extend(analyse.consommations)

        if analyse.resultat is None:
            # L'Analyste a juge la question sans reponse dans ce schema : son
            # explication EST la reponse. Personne d'autre n'a de travail.
            etapes.extend(_etapes_sans_resultat())
            return ReponseComplete(
                question=question,
                reponse=analyse.plan.explication,
                sql=None,
                resultat=None,
                etapes=etapes,
                consommations=consommations,
                duree_ms=_ms(depart),
            )
        return await self._finir(question, analyse, etapes, consommations, depart)

    async def _finir(
        self,
        question: str,
        analyse: ResultatAnalyse,
        etapes: list[Etape],
        consommations: list[Consommation],
        depart: float,
    ) -> ReponseComplete:
        assert analyse.resultat is not None
        serie = self._etape_ml(analyse.resultat, etapes)
        (redaction, etape_redaction), (viz, etape_viz) = await asyncio.gather(
            self._etape_redaction(question, analyse, serie),
            self._etape_viz(question, analyse.resultat),
        )
        etapes.extend([etape_redaction, etape_viz])
        consommations.append(redaction.consommation)
        if viz is not None:
            consommations.append(viz.consommation)

        return ReponseComplete(
            question=question,
            reponse=redaction.contenu.reponse,
            sql=analyse.sql_execute,
            resultat=analyse.resultat,
            analyse=serie,
            graphique=viz.contenu if viz is not None and viz.contenu.type != "aucun" else None,
            etapes=etapes,
            consommations=consommations,
            duree_ms=_ms(depart),
        )

    async def _etape_data(self, etapes: list[Etape]) -> ContexteDonnees:
        depart = time.perf_counter()
        try:
            contexte = await asyncio.to_thread(self._data.decrire)
        except ErreurRequete as erreur:
            etapes.append(Etape("data", "refusee", _ms(depart), erreur.raison))
            raise ErreurUtilisateur(erreur.raison, code_http=502) from erreur

        if contexte.est_vide:
            etapes.append(Etape("data", "refusee", _ms(depart), "entrepot vide"))
            raise ErreurUtilisateur(
                "Aucune table n'est encore dans votre entrepot. Connectez une source et "
                "synchronisez-la avant de poser une question.",
                code_http=409,
            )
        detail = contexte.resume() + (" — deja en memoire" if contexte.depuis_cache else "")
        etapes.append(Etape("data", "terminee", _ms(depart), detail))
        return contexte

    async def _etape_analyse(
        self,
        question: str,
        schema: str,
        etapes: list[Etape],
        historique: list[Echange] | tuple[Echange, ...],
    ) -> ResultatAnalyse:
        depart = time.perf_counter()
        try:
            analyse = await self._analyste.repondre(question, schema, historique)
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

    def _etape_ml(self, resultat: Resultat, etapes: list[Etape]) -> AnalyseSerie | None:
        depart = time.perf_counter()
        try:
            serie = self._ml.analyser(resultat)
        except (ValueError, TypeError, ArithmeticError):
            # Une forme de resultat qu'on n'avait pas prevue ne doit pas
            # priver l'utilisateur de sa reponse : on le note, on continue.
            logger.exception(
                "L'agent ML a echoue sur un resultat de %s colonnes", len(resultat.colonnes)
            )
            etapes.append(Etape("ml", "refusee", _ms(depart), "analyse impossible sur ce resultat"))
            return None
        if serie is None:
            etapes.append(Etape("ml", "ignoree", _ms(depart), "pas une serie a analyser"))
            return None
        detail = f"{serie.tendance}, {len(serie.anomalies)} anomalie(s)"
        etapes.append(Etape("ml", "terminee", _ms(depart), detail))
        return serie

    async def _etape_redaction(
        self, question: str, analyse: ResultatAnalyse, serie: AnalyseSerie | None
    ) -> tuple[Reponse[Redaction], Etape]:
        depart = time.perf_counter()
        assert analyse.sql_execute is not None and analyse.resultat is not None
        redaction = await self._redacteur.rediger(
            question,
            analyse.sql_execute,
            analyse.resultat,
            serie.resume() if serie is not None else None,
        )
        return redaction, Etape("redacteur", "terminee", _ms(depart))

    async def _etape_viz(
        self, question: str, resultat: Resultat
    ) -> tuple[Reponse[SpecGraphique] | None, Etape]:
        depart = time.perf_counter()
        motif = self._viz.motif_de_refus(resultat)
        if motif:
            return None, Etape("viz", "ignoree", _ms(depart), motif)
        try:
            reponse = await self._viz.choisir(question, resultat)
        except ErreurUtilisateur as erreur:
            # Un graphique en moins ne vaut pas une reponse en moins.
            return None, Etape("viz", "refusee", _ms(depart), erreur.message)
        spec = reponse.contenu
        detail = spec.type if spec.type != "aucun" else f"aucun graphique : {spec.raison}"
        return reponse, Etape("viz", "terminee", _ms(depart), detail)


def _etapes_sans_resultat() -> list[Etape]:
    return [
        Etape("ml", "ignoree", 0, "pas de resultat"),
        Etape("redacteur", "ignoree", 0, "rien a formuler"),
        Etape("viz", "ignoree", 0, "pas de resultat"),
    ]


def _ms(depart: float) -> int:
    return int((time.perf_counter() - depart) * 1000)
