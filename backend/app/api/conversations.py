"""Routes des fils de conversation d'un espace, et des questions qu'on y pose."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AccesEspace, acces_analyste, acces_courant, utilisateur_courant
from app.api.questions import en_reponse
from app.core.database import get_db
from app.core.llm_client import LLMClient, get_llm_client
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreation,
    ConversationModification,
    ConversationReponse,
)
from app.schemas.question import QuestionDemande, QuestionReponse
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/espaces/{espace_id}/conversations", tags=["assistant"])


@router.get("", response_model=list[ConversationReponse])
async def lister(acces: AccesEspace = Depends(acces_courant), db: AsyncSession = Depends(get_db)):
    fils = await ConversationService(db).lister(acces.espace)
    return [_en_reponse(c, nb, auteur) for c, nb, auteur in fils]


@router.post("", response_model=ConversationReponse, status_code=201)
async def creer(
    demande: ConversationCreation,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    conversation = await ConversationService(db).creer(acces.espace, utilisateur, demande.titre)
    return _en_reponse(conversation, 0, utilisateur)


@router.patch("/{conversation_id}", response_model=ConversationReponse)
async def modifier(
    conversation_id: str,
    demande: ConversationModification,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    conversation = await service.charger(acces.espace, conversation_id)
    conversation = await service.modifier(conversation, demande.titre, demande.epinglee)
    return _en_reponse(
        conversation, len(await service.questions(conversation)), await _auteur(db, conversation)
    )


@router.delete("/{conversation_id}", status_code=204)
async def supprimer(
    conversation_id: str,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    conversation = await service.charger(acces.espace, conversation_id)
    await service.supprimer(conversation, utilisateur, acces.role)


@router.get("/{conversation_id}/questions", response_model=list[QuestionReponse])
async def questions(
    conversation_id: str,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    conversation = await service.charger(acces.espace, conversation_id)
    return [en_reponse(q) for q in await service.questions(conversation)]


@router.post("/{conversation_id}/questions", response_model=QuestionReponse, status_code=201)
async def poser(
    conversation_id: str,
    demande: QuestionDemande,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    conversation = await ConversationService(db).charger(acces.espace, conversation_id)
    question = await ChatService(db, llm).poser(
        acces.espace, utilisateur, conversation, demande.texte
    )
    return en_reponse(question)


def _en_reponse(conversation: Conversation, nb_questions: int, auteur: User) -> ConversationReponse:
    return ConversationReponse(
        id=conversation.id,
        titre=conversation.titre,
        epinglee=conversation.epinglee,
        nb_questions=nb_questions,
        auteur=auteur.nom_complet,
        auteur_id=auteur.id,
        cree_le=conversation.cree_le,
        maj_le=conversation.maj_le,
    )


async def _auteur(db: AsyncSession, conversation: Conversation) -> User:
    auteur = await db.get(User, conversation.user_id)
    assert auteur is not None
    return auteur
