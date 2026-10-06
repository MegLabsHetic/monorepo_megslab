"""Les surveillances d'un espace : des questions qui se posent toutes seules.

Executer a la main est expose deliberement : personne ne doit decouvrir le
comportement de sa surveillance le lendemain matin, dans une notification.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AccesEspace, acces_analyste, acces_courant, utilisateur_courant
from app.core.database import get_db
from app.models.surveillance import Surveillance
from app.models.user import User
from app.schemas.surveillance import (
    SurveillanceDemande,
    SurveillanceReponse,
    VerdictReponse,
)
from app.services.surveillance_service import SurveillanceService

router = APIRouter(prefix="/espaces/{espace_id}/surveillances", tags=["surveillances"])


def _reponse(s: Surveillance) -> SurveillanceReponse:
    return SurveillanceReponse(
        id=s.id,
        titre=s.titre,
        sql=s.sql,
        declencheur=s.declencheur,
        seuil=s.seuil,
        heure=s.heure,
        active=s.active,
        derniere_execution=s.derniere_execution,
        dernier_etat=s.dernier_etat,
    )


@router.get("", response_model=list[SurveillanceReponse])
async def lister(
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    return [_reponse(s) for s in await SurveillanceService(db).lister(acces.espace)]


@router.post("", response_model=SurveillanceReponse, status_code=201)
async def creer(
    demande: SurveillanceDemande,
    acces: AccesEspace = Depends(acces_analyste),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    surveillance = await SurveillanceService(db).creer(
        acces.espace,
        utilisateur,
        demande.titre,
        demande.sql,
        demande.declencheur,
        demande.seuil,
        demande.heure,
    )
    return _reponse(surveillance)


@router.post("/{surveillance_id}/executer", response_model=VerdictReponse)
async def executer(
    surveillance_id: str,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    """Declenche la surveillance maintenant, pour voir ce qu'elle dirait."""
    service = SurveillanceService(db)
    surveillance = await service.charger(acces.espace, surveillance_id)
    verdict = await service.executer(acces.espace, surveillance)
    return VerdictReponse(notifier=verdict.notifier, message=verdict.message, erreur=verdict.erreur)


@router.patch("/{surveillance_id}", response_model=SurveillanceReponse)
async def basculer(
    surveillance_id: str,
    active: bool,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    surveillance = await SurveillanceService(db).basculer(acces.espace, surveillance_id, active)
    return _reponse(surveillance)


@router.delete("/{surveillance_id}", status_code=204)
async def supprimer(
    surveillance_id: str,
    acces: AccesEspace = Depends(acces_analyste),
    db: AsyncSession = Depends(get_db),
):
    await SurveillanceService(db).supprimer(acces.espace, surveillance_id)
