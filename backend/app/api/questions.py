"""Routes de l'assistant a l'echelle d'un espace : toutes les questions, le contexte."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AccesEspace, acces_courant
from app.core.database import get_db
from app.models.question import Question
from app.schemas.question import (
    AnalyseReponse,
    ContexteReponse,
    EtapeReponse,
    GraphiqueReponse,
    QuestionReponse,
    ResultatReponse,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/espaces/{espace_id}/questions", tags=["assistant"])


@router.get("", response_model=list[QuestionReponse])
async def historique(
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    """Toutes les questions de l'espace, les plus recentes d'abord : sert aux
    compteurs d'usage et de cout."""
    questions = await ChatService(db).historique(acces.espace)
    return [en_reponse(question) for question in questions]


@router.get("/contexte", response_model=ContexteReponse)
async def contexte(
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    """Ce que le modele recoit reellement. Lu dans l'entrepot, pas simule."""
    contexte, instructions = await ChatService(db).contexte(acces.espace)
    return ContexteReponse(
        schema=contexte.texte(),
        instructions=instructions,
        nb_tables=contexte.nb_tables,
        nb_colonnes=contexte.nb_colonnes,
        nb_lignes=contexte.nb_lignes,
    )


def en_reponse(question: Question) -> QuestionReponse:
    resultat = question.resultat
    return QuestionReponse(
        id=question.id,
        conversation_id=question.conversation_id,
        texte=question.texte,
        reponse=question.reponse,
        sql=question.sql,
        resultat=ResultatReponse(**resultat) if resultat else None,
        analyse=AnalyseReponse(**question.analyse) if question.analyse else None,
        graphique=GraphiqueReponse(**question.graphique) if question.graphique else None,
        etapes=[EtapeReponse(**etape) for etape in question.etapes or []],
        cout_dollars=question.cout_dollars,
        jetons=question.jetons,
        duree_ms=question.duree_ms,
        cree_le=question.cree_le,
    )
