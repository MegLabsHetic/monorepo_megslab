"""Les fils de conversation d'un espace."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.conversation import TITRE_MAX, Conversation
from app.models.membership import Role
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace

TITRE_PAR_DEFAUT = "Nouvelle conversation"


class ConversationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def lister(self, espace: Workspace) -> list[tuple[Conversation, int, User]]:
        """Chaque conversation de l'espace avec son nombre de questions et son auteur,
        epinglees d'abord, puis les plus recemment actives."""
        nb_questions = (
            select(Question.conversation_id, func.count().label("nb"))
            .group_by(Question.conversation_id)
            .subquery()
        )
        resultat = await self._db.execute(
            select(Conversation, func.coalesce(nb_questions.c.nb, 0), User)
            .join(User, User.id == Conversation.user_id)
            .outerjoin(nb_questions, nb_questions.c.conversation_id == Conversation.id)
            .where(Conversation.workspace_id == espace.id)
            .order_by(Conversation.epinglee.desc(), Conversation.maj_le.desc())
        )
        return [(conversation, int(nb), auteur) for conversation, nb, auteur in resultat.all()]

    async def creer(self, espace: Workspace, utilisateur: User, titre: str | None) -> Conversation:
        conversation = Conversation(
            workspace_id=espace.id,
            user_id=utilisateur.id,
            titre=_titre(titre) or TITRE_PAR_DEFAUT,
        )
        self._db.add(conversation)
        await self._db.commit()
        await self._db.refresh(conversation)
        return conversation

    async def charger(self, espace: Workspace, conversation_id: str) -> Conversation:
        conversation = await self._db.get(Conversation, conversation_id)
        if conversation is None or conversation.workspace_id != espace.id:
            raise ErreurUtilisateur("Conversation introuvable.", code_http=404)
        return conversation

    async def modifier(
        self, conversation: Conversation, titre: str | None, epinglee: bool | None
    ) -> Conversation:
        if titre is not None:
            conversation.titre = _titre(titre) or conversation.titre
        if epinglee is not None:
            conversation.epinglee = epinglee
        await self._db.commit()
        await self._db.refresh(conversation)
        return conversation

    async def supprimer(self, conversation: Conversation, utilisateur: User, role: Role) -> None:
        """L'auteur ou un admin de l'espace. Les questions du fil partent avec lui."""
        if conversation.user_id != utilisateur.id and role != Role.ADMIN:
            raise ErreurUtilisateur(
                "Seul l'auteur ou un admin de l'espace peut supprimer ce fil.", code_http=403
            )
        questions = await self._db.execute(
            select(Question).where(Question.conversation_id == conversation.id)
        )
        for question in questions.scalars():
            await self._db.delete(question)
        await self._db.delete(conversation)
        await self._db.commit()

    async def questions(self, conversation: Conversation) -> list[Question]:
        resultat = await self._db.execute(
            select(Question)
            .where(Question.conversation_id == conversation.id)
            .order_by(Question.cree_le)
        )
        return list(resultat.scalars())


def _titre(texte: str | None) -> str:
    propre = " ".join((texte or "").split())
    return propre if len(propre) <= TITRE_MAX else propre[: TITRE_MAX - 1] + "…"


def titre_depuis_question(texte: str) -> str:
    """Le titre d'un fil neuf : sa premiere question, coupee proprement."""
    propre = " ".join(texte.split())
    return propre if len(propre) <= 60 else propre[:59].rstrip() + "…"
