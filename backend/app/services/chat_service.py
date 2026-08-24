"""Pose une question a l'assistant et conserve ce qu'elle a produit.

Le contexte envoye au modele est lu dans l'entrepot de l'organisation par
l'agent Data : rien de ce que le modele voit ne vient d'ailleurs, et
l'interface peut le montrer tel quel.
"""

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyste import INSTRUCTIONS as INSTRUCTIONS_ANALYSTE
from app.agents.data import AgentData, ContexteDonnees
from app.agents.orchestrateur import Orchestrateur, ReponseComplete
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import LLMClient
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User

logger = logging.getLogger(__name__)

# Le resultat conserve n'est pas la table entiere : le SQL est garde et peut
# etre rejoue. On stocke ce qu'il faut pour relire une reponse sans requete.
LIGNES_CONSERVEES = 200


class ChatService:
    def __init__(
        self,
        db: AsyncSession,
        llm: LLMClient | None = None,
        fabrique_moteur: Callable[[str], DuckDBEngine] = DuckDBEngine,
    ) -> None:
        self._db = db
        self._llm = llm
        # Injectable pour tester sans entrepot : le vrai moteur ouvre une
        # connexion reseau a chaque appel.
        self._fabrique_moteur = fabrique_moteur

    async def poser(self, organisation: Organization, utilisateur: User, texte: str) -> Question:
        moteur = self._fabrique_moteur(f"org_{organisation.id}")
        complete = await Orchestrateur(moteur, self._llm).repondre(texte)
        question = self._en_question(organisation, utilisateur, complete)
        self._db.add(question)
        await self._db.commit()
        await self._db.refresh(question)
        logger.info(
            "Question %s : %s jetons, $%.4f, %s ms",
            question.id,
            question.jetons,
            question.cout_dollars,
            question.duree_ms,
        )
        return question

    async def contexte(self, organisation: Organization) -> tuple[ContexteDonnees, str]:
        """Ce qui partirait au modele pour cette organisation, maintenant."""
        moteur = self._fabrique_moteur(f"org_{organisation.id}")
        try:
            contexte = await asyncio.to_thread(AgentData(moteur).decrire)
        except ErreurRequete as erreur:
            raise ErreurUtilisateur(erreur.raison, code_http=502) from erreur
        return contexte, INSTRUCTIONS_ANALYSTE

    async def historique(self, organisation: Organization, limite: int = 50) -> list[Question]:
        resultat = await self._db.execute(
            select(Question)
            .where(Question.organization_id == organisation.id)
            .order_by(Question.cree_le.desc())
            .limit(limite)
        )
        return list(resultat.scalars().all())

    @staticmethod
    def _en_question(
        organisation: Organization, utilisateur: User, complete: ReponseComplete
    ) -> Question:
        return Question(
            organization_id=organisation.id,
            user_id=utilisateur.id,
            texte=complete.question,
            reponse=complete.reponse,
            sql=complete.sql,
            nb_lignes=complete.resultat.nb_lignes if complete.resultat else None,
            resultat=_extrait(complete.resultat) if complete.resultat else None,
            analyse=complete.analyse.en_dict() if complete.analyse else None,
            graphique=complete.graphique.model_dump() if complete.graphique else None,
            etapes=[
                {"agent": e.agent, "statut": e.statut, "duree_ms": e.duree_ms, "detail": e.detail}
                for e in complete.etapes
            ],
            cout_dollars=complete.cout_dollars,
            jetons=complete.jetons,
            duree_ms=complete.duree_ms,
        )


def _extrait(resultat) -> dict:
    """Les premieres lignes, rendues stockables en JSON.

    Decimal, date et UUID n'existent pas en JSON : ils deviennent du texte. Les
    types simples restent tels quels pour que l'interface aligne encore les
    nombres a droite.
    """
    lignes = resultat.lignes[:LIGNES_CONSERVEES]
    return {
        "colonnes": resultat.colonnes,
        "lignes": [[_json_sur(valeur) for valeur in ligne] for ligne in lignes],
        "tronque": resultat.tronque or len(resultat.lignes) > LIGNES_CONSERVEES,
    }


def _json_sur(valeur: object) -> object:
    if valeur is None or isinstance(valeur, (bool, int, float, str)):
        return valeur
    return str(valeur)
