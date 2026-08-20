"""Routes de l'assistant : poser une question, relire l'historique, voir le contexte."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import organisation_courante, utilisateur_courant
from app.core.database import get_db
from app.core.llm_client import LLMClient, get_llm_client
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User
from app.schemas.question import (
    ContexteReponse,
    EtapeReponse,
    QuestionDemande,
    QuestionReponse,
    ResultatReponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/questions", tags=["assistant"])


@router.post("", response_model=QuestionReponse, status_code=201)
async def poser(
    demande: QuestionDemande,
    organisation: Organization = Depends(organisation_courante),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
    llm: LLMClient = Depends(get_llm_client),
):
    question = await ChatService(db, llm).poser(organisation, utilisateur, demande.texte)
    return _en_reponse(question)


@router.get("", response_model=list[QuestionReponse])
async def historique(
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    questions = await ChatService(db).historique(organisation)
    return [_en_reponse(question) for question in questions]


@router.get("/contexte", response_model=ContexteReponse)
async def contexte(
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    """Ce que le modele recoit reellement. Lu dans l'entrepot, pas simule."""
    schema, instructions = await ChatService(db).contexte(organisation)
    return ContexteReponse(schema=schema, instructions=instructions)


def _en_reponse(question: Question) -> QuestionReponse:
    resultat = question.resultat
    return QuestionReponse(
        id=question.id,
        texte=question.texte,
        reponse=question.reponse,
        sql=question.sql,
        resultat=ResultatReponse(**resultat) if resultat else None,
        etapes=[EtapeReponse(**etape) for etape in question.etapes or []],
        cout_dollars=question.cout_dollars,
        jetons=question.jetons,
        duree_ms=question.duree_ms,
        cree_le=question.cree_le,
    )
