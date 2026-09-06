"""Routes de l'assistant a l'echelle d'un espace : toutes les questions, le contexte."""

import asyncio
import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AccesEspace, acces_courant
from app.core.database import get_db
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete
from app.core.errors import ErreurUtilisateur
from app.core.sql_guard import SqlRefuse, valider
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


@router.get("/{question_id}/export.csv")
async def exporter(
    question_id: str,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    """Le resultat complet de la requete, rejouee a l'instant, en CSV pour Excel.

    La reponse conservee ne garde qu'un extrait ; l'export re-execute le SQL
    valide, jusqu'a la limite du moteur (cinq mille lignes).
    """
    question = await db.get(Question, question_id)
    if question is None or question.workspace_id != acces.espace.id:
        raise ErreurUtilisateur("Question introuvable.", code_http=404)
    if not question.sql:
        raise ErreurUtilisateur("Cette reponse n'a pas de requete a exporter.", code_http=422)
    try:
        resultat = await asyncio.to_thread(
            DuckDBEngine(acces.espace.schema_entrepot).executer, valider(question.sql)
        )
    except (SqlRefuse, ErreurRequete) as erreur:
        raise ErreurUtilisateur(erreur.raison, code_http=502) from erreur

    tampon = io.StringIO()
    ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\n")
    ecrivain.writerow(resultat.colonnes)
    for ligne in resultat.lignes:
        ecrivain.writerow(["" if v is None else v for v in ligne])
    return Response(
        content="﻿" + tampon.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="meglabs-{question.id[:8]}.csv"'},
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
