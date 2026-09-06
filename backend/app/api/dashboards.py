"""Routes des tableaux de bord d'un espace : lister, creer, epingler, rejouer."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AccesEspace, acces_analyste, acces_courant, utilisateur_courant
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.dashboard import Dashboard
from app.models.question import Question
from app.models.user import User
from app.schemas.dashboard import (
    DashboardCreation,
    DashboardDetailReponse,
    DashboardModification,
    DashboardReponse,
    EpinglageDemande,
    WidgetModification,
    WidgetReponse,
)
from app.schemas.question import AnalyseReponse, GraphiqueReponse, ResultatReponse
from app.services.chat_service import extrait_json
from app.services.dashboard_service import DashboardService, WidgetVivant

router = APIRouter(prefix="/espaces/{espace_id}/dashboards", tags=["dashboards"])


@router.get("", response_model=list[DashboardReponse])
async def lister(acces: AccesEspace = Depends(acces_courant), db: AsyncSession = Depends(get_db)):
    return [_resume(d, nb, u) for d, nb, u in await DashboardService(db).lister(acces.espace)]


@router.post("", response_model=DashboardReponse, status_code=201)
async def creer(
    demande: DashboardCreation,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    dashboard = await DashboardService(db).creer(acces.espace, utilisateur, demande.nom)
    return _resume(dashboard, 0, utilisateur)


@router.get("/{dashboard_id}", response_model=DashboardDetailReponse)
async def detail(
    dashboard_id: str,
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    """Le tableau avec ses requetes rejouees a l'instant sur l'entrepot."""
    service = DashboardService(db)
    dashboard = await service.charger(acces.espace, dashboard_id)
    vivants = await service.rafraichir(acces.espace, dashboard)
    auteur = await db.get(User, dashboard.user_id)
    assert auteur is not None
    return DashboardDetailReponse(
        id=dashboard.id,
        nom=dashboard.nom,
        auteur=auteur.nom_complet,
        auteur_id=auteur.id,
        cree_le=dashboard.cree_le,
        maj_le=dashboard.maj_le,
        widgets=[await _widget(db, v) for v in vivants],
        rejoue_le=datetime.now(UTC),
    )


@router.patch("/{dashboard_id}", response_model=DashboardReponse)
async def renommer(
    dashboard_id: str,
    demande: DashboardModification,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    dashboard = await service.renommer(
        await service.charger(acces.espace, dashboard_id), demande.nom
    )
    auteur = await db.get(User, dashboard.user_id)
    assert auteur is not None
    return _resume(dashboard, len(dashboard.widgets), auteur)


@router.delete("/{dashboard_id}", status_code=204)
async def supprimer(
    dashboard_id: str,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    await service.supprimer(
        await service.charger(acces.espace, dashboard_id), utilisateur, acces.role
    )


@router.post("/{dashboard_id}/widgets", response_model=WidgetReponse, status_code=201)
async def epingler(
    dashboard_id: str,
    demande: EpinglageDemande,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    dashboard = await service.charger(acces.espace, dashboard_id)
    question = await db.get(Question, demande.question_id)
    if question is None or question.workspace_id != acces.espace.id:
        raise ErreurUtilisateur("Question introuvable.", code_http=404)
    widget = await service.epingler(dashboard, question, demande.titre)
    return await _widget(db, WidgetVivant(widget, None, None, None))


@router.patch("/{dashboard_id}/widgets/{widget_id}", response_model=WidgetReponse)
async def modifier_widget(
    dashboard_id: str,
    widget_id: str,
    demande: WidgetModification,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    dashboard = await service.charger(acces.espace, dashboard_id)
    widget = await service.modifier_widget(dashboard, widget_id, demande.titre, demande.position)
    return await _widget(db, WidgetVivant(widget, None, None, None))


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def retirer_widget(
    dashboard_id: str,
    widget_id: str,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    service = DashboardService(db)
    await service.retirer_widget(await service.charger(acces.espace, dashboard_id), widget_id)


def _resume(dashboard: Dashboard, nb_widgets: int, auteur: User) -> DashboardReponse:
    return DashboardReponse(
        id=dashboard.id,
        nom=dashboard.nom,
        nb_widgets=nb_widgets,
        auteur=auteur.nom_complet,
        auteur_id=auteur.id,
        cree_le=dashboard.cree_le,
        maj_le=dashboard.maj_le,
    )


async def _widget(db: AsyncSession, vivant: WidgetVivant) -> WidgetReponse:
    widget = vivant.widget
    conversation_id = None
    if widget.question_id:
        question = await db.get(Question, widget.question_id)
        conversation_id = question.conversation_id if question else None
    return WidgetReponse(
        id=widget.id,
        titre=widget.titre,
        sql=widget.sql,
        question_id=widget.question_id,
        conversation_id=conversation_id,
        position=widget.position,
        graphique=GraphiqueReponse(**widget.graphique) if widget.graphique else None,
        resultat=ResultatReponse(**extrait_json(vivant.resultat)) if vivant.resultat else None,
        analyse=AnalyseReponse(**vivant.analyse.en_dict()) if vivant.analyse else None,
        erreur=vivant.erreur,
    )
