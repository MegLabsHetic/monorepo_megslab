"""L'agent Analyste : traduit une question en francais en SQL, puis l'execute.

Le SQL produit par le modele n'est jamais execute tel quel. Il passe par
`sql_guard`, qui le rejette s'il n'est pas une lecture et le regenere depuis son
arbre syntaxique. Le modele propose ; le garde-fou dispose.

Quand l'entrepot rejette la requete, l'Analyste a droit a une reprise : il voit
l'erreur du moteur et repropose. Une seule — au-dela, insister couterait sans
garantie, et l'utilisateur merite de savoir que ca n'a pas marche.
"""

import logging
from dataclasses import dataclass

from pydantic import BaseModel, Field

from app.core.duckdb_engine import DuckDBEngine, ErreurRequete, Resultat
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import Consommation, LLMClient, Reponse
from app.core.sql_guard import SqlRefuse, valider

logger = logging.getLogger(__name__)

INSTRUCTIONS = """Tu es analyste de donnees. Tu traduis une question posee en francais
en UNE requete SQL DuckDB, executee sur un entrepot en lecture seule.

Regles absolues :
- Uniquement SELECT ou WITH. Jamais INSERT, UPDATE, DELETE, CREATE, DROP, ALTER.
- N'utilise que les tables et colonnes listees dans le schema fourni. N'en invente aucune.
- Prefixe chaque table par le schema : entrepot."nom_de_table".
- Limite les resultats a 1000 lignes au maximum.
- Si la question ne peut pas etre repondue avec ce schema, laisse `sql` vide et
  explique pourquoi dans `explication`.

Les types indiques sont ceux de l'entrepot, tels quels. Une date ou un nombre
stockes en VARCHAR doivent etre convertis explicitement (TRY_CAST(... AS TIMESTAMP),
TRY_CAST(... AS DOUBLE)) avant tout calcul, toute comparaison ou tout tri.

Si on te renvoie une requete avec l'erreur que le moteur a produite, corrige-la
sans changer ce qu'elle calcule.

Si des echanges precedents sont fournis, la question s'inscrit dans leur suite :
« et par etat ? » reprend la mesure de la question d'avant en changeant l'axe.
Appuie-toi sur leur SQL, ne repars pas de zero.

Ecris un SQL lisible : des alias explicites, des noms de colonnes de sortie en francais
quand cela aide a la lecture."""


class PlanRequete(BaseModel):
    """Ce que l'Analyste rend avant toute execution."""

    sql: str = Field(description="La requete SQL, ou une chaine vide si impossible")
    tables_utilisees: list[str] = Field(default_factory=list)
    explication: str = Field(description="Ce que la requete calcule, en francais")


@dataclass(frozen=True)
class Echange:
    """Un echange precedent du meme fil, tel que l'Analyste le recoit."""

    question: str
    sql: str | None
    reponse: str


class ResultatAnalyse:
    """Le SQL produit, ce qu'il a renvoye, et ce que chaque appel a coute."""

    def __init__(
        self,
        plan: PlanRequete,
        resultat: Resultat | None,
        consommations: list[Consommation],
        sql_execute: str | None,
        corrigee: bool = False,
    ) -> None:
        self.plan = plan
        self.resultat = resultat
        self.consommations = consommations
        self.sql_execute = sql_execute
        self.corrigee = corrigee


class Analyste:
    def __init__(self, moteur: DuckDBEngine, llm: LLMClient | None = None) -> None:
        self._moteur = moteur
        self._llm = llm or LLMClient()

    async def repondre(
        self, question: str, schema: str, historique: list[Echange] | tuple[Echange, ...] = ()
    ) -> ResultatAnalyse:
        instructions = f"{INSTRUCTIONS}\n\nSchema disponible :\n{schema}"
        texte = _composer(question, historique)
        reponse = await self._proposer(instructions, texte)
        plan, consommations = reponse.contenu, [reponse.consommation]

        if not plan.sql.strip():
            return ResultatAnalyse(plan, None, consommations, None)

        sql_execute = self._valider(plan.sql)
        try:
            resultat = self._moteur.executer(sql_execute)
        except ErreurRequete as erreur:
            return await self._corriger(instructions, texte, sql_execute, erreur, consommations)
        return ResultatAnalyse(plan, resultat, consommations, sql_execute)

    async def _corriger(
        self,
        instructions: str,
        question: str,
        sql_fautif: str,
        erreur: ErreurRequete,
        consommations: list[Consommation],
    ) -> ResultatAnalyse:
        """La reprise : le modele voit l'erreur exacte du moteur et repropose."""
        logger.info("Requete rejetee par le moteur, correction demandee : %s", erreur.detail)
        reponse = await self._proposer(
            instructions, _demande_correction(question, sql_fautif, erreur)
        )
        plan = reponse.contenu
        consommations.append(reponse.consommation)

        if not plan.sql.strip():
            return ResultatAnalyse(plan, None, consommations, None, corrigee=True)

        sql_execute = self._valider(plan.sql)
        resultat = self._executer(sql_execute)
        return ResultatAnalyse(plan, resultat, consommations, sql_execute, corrigee=True)

    async def _proposer(self, instructions: str, question: str) -> Reponse[PlanRequete]:
        return await self._llm.repondre(
            instructions=instructions,
            question=question,
            format_sortie=PlanRequete,
            effort="medium",
        )

    def _valider(self, sql: str) -> str:
        """Le SQL du modele passe par le garde-fou avant d'approcher la base."""
        try:
            return valider(sql)
        except SqlRefuse as refus:
            logger.warning("SQL refuse par le garde-fou : %s", refus.raison)
            raise ErreurUtilisateur(
                f"La requete produite a ete refusee : {refus.raison}", code_http=422
            ) from refus

    def _executer(self, sql: str) -> Resultat:
        try:
            return self._moteur.executer(sql)
        except ErreurRequete as erreur:
            raise ErreurUtilisateur(erreur.raison, code_http=422) from erreur


def _composer(question: str, historique: list[Echange] | tuple[Echange, ...]) -> str:
    """La question, precedee des derniers echanges du fil s'il y en a."""
    if not historique:
        return question
    blocs = []
    for i, echange in enumerate(historique, start=1):
        sql = echange.sql or "(aucune requete : la question etait sans reponse)"
        blocs.append(
            f"Echange {i}\nQuestion : {echange.question}\nSQL : {sql}\nReponse : {echange.reponse}"
        )
    return (
        "Echanges precedents, du plus ancien au plus recent :\n\n"
        + "\n\n".join(blocs)
        + f"\n\nNouvelle question : {question}"
    )


def _demande_correction(question: str, sql: str, erreur: ErreurRequete) -> str:
    return (
        f"{question}\n\n"
        f"Ta requete precedente :\n{sql}\n\n"
        f"Le moteur l'a rejetee avec cette erreur :\n{erreur.detail or erreur.raison}\n\n"
        "Corrige la requete sans changer ce qu'elle calcule."
    )


def decrire_schema(tables: list[tuple[str, list[tuple[str, str]]]]) -> str:
    """Met le schema sous la forme la plus courte qui reste sans ambiguite.

    Seuls les noms de tables, de colonnes et leurs types partent au modele —
    aucune donnee.
    """
    return "\n".join(
        f'- entrepot."{table}" ({", ".join(f"{nom} {type_}" for nom, type_ in colonnes)})'
        for table, colonnes in tables
    )
