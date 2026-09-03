"""Pose une question dans un fil et conserve ce qu'elle a produit.

Le contexte envoye au modele est lu dans l'entrepot de l'espace par l'agent
Data : rien de ce que le modele voit ne vient d'ailleurs, et l'interface peut
le montrer tel quel. Les derniers echanges du fil sont transmis a l'Analyste,
pour qu'une question de suivi (« et par etat ? ») soit comprise.
"""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.analyste import INSTRUCTIONS as INSTRUCTIONS_ANALYSTE
from app.agents.analyste import Echange
from app.agents.data import AgentData, ContexteDonnees
from app.agents.orchestrateur import Orchestrateur, ReponseComplete
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete
from app.core.errors import ErreurUtilisateur
from app.core.llm_client import LLMClient
from app.models.conversation import Conversation
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace
from app.services.conversation_service import TITRE_PAR_DEFAUT, titre_depuis_question

logger = logging.getLogger(__name__)

# Le resultat conserve n'est pas la table entiere : le SQL est garde et peut
# etre rejoue. On stocke ce qu'il faut pour relire une reponse sans requete.
LIGNES_CONSERVEES = 200
# Au-dela, le contexte de conversation coute plus de jetons qu'il n'aide.
ECHANGES_TRANSMIS = 3


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

    async def poser(
        self, espace: Workspace, utilisateur: User, conversation: Conversation, texte: str
    ) -> Question:
        moteur = self._fabrique_moteur(espace.schema_entrepot)
        precedents = await self._derniers_echanges(conversation)
        complete = await Orchestrateur(moteur, self._llm).repondre(texte, precedents)

        question = self._en_question(espace, utilisateur, conversation, complete)
        self._db.add(question)
        if not precedents and conversation.titre == TITRE_PAR_DEFAUT:
            conversation.titre = titre_depuis_question(texte)
        # Une question ajoutee doit faire remonter le fil, meme sans autre changement.
        conversation.maj_le = datetime.now(UTC)
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

    async def contexte(self, espace: Workspace) -> tuple[ContexteDonnees, str]:
        """Ce qui partirait au modele pour cet espace, maintenant."""
        moteur = self._fabrique_moteur(espace.schema_entrepot)
        try:
            contexte = await asyncio.to_thread(AgentData(moteur).decrire)
        except ErreurRequete as erreur:
            raise ErreurUtilisateur(erreur.raison, code_http=502) from erreur
        return contexte, INSTRUCTIONS_ANALYSTE

    async def historique(self, espace: Workspace, limite: int = 200) -> list[Question]:
        """Toutes les questions de l'espace, les plus recentes d'abord : sert aux
        compteurs d'usage et de cout, pas a relire un fil."""
        resultat = await self._db.execute(
            select(Question)
            .where(Question.workspace_id == espace.id)
            .order_by(Question.cree_le.desc())
            .limit(limite)
        )
        return list(resultat.scalars().all())

    async def _derniers_echanges(self, conversation: Conversation) -> list[Echange]:
        resultat = await self._db.execute(
            select(Question)
            .where(Question.conversation_id == conversation.id)
            .order_by(Question.cree_le.desc())
            .limit(ECHANGES_TRANSMIS)
        )
        recents = list(resultat.scalars())
        return [Echange(q.texte, q.sql, q.reponse) for q in reversed(recents)]

    @staticmethod
    def _en_question(
        espace: Workspace, utilisateur: User, conversation: Conversation, complete: ReponseComplete
    ) -> Question:
        return Question(
            workspace_id=espace.id,
            conversation_id=conversation.id,
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
