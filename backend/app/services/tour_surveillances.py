"""Ce que l'ordonnanceur execute a chaque heure : les surveillances du moment.

Ce module fait le lien entre une horloge et le service : il ouvre sa propre
session de base, parcourt les espaces, et laisse `SurveillanceService` decider
de notifier ou non. Il ne connait ni le modele ni l'entrepot.
"""

import logging

from sqlalchemy import select

from app.core.database import creer_session
from app.models.surveillance import Surveillance
from app.models.workspace import Workspace
from app.services.surveillance_service import SurveillanceService

logger = logging.getLogger(__name__)


async def executer_les_surveillances(heure: int) -> int:
    """Execute les surveillances actives programmees a cette heure.

    Rend le nombre de surveillances executees. Une qui echoue n'empeche pas les
    suivantes : une requete devenue invalide ne doit pas eteindre la
    surveillance de tout le monde.
    """
    executees = 0
    async with creer_session() as db:
        resultat = await db.execute(
            select(Surveillance).where(Surveillance.active.is_(True), Surveillance.heure == heure)
        )
        surveillances = list(resultat.scalars())
        if not surveillances:
            return 0
        service = SurveillanceService(db)
        for surveillance in surveillances:
            espace = await db.get(Workspace, surveillance.workspace_id)
            if espace is None:
                continue
            try:
                verdict = await service.executer(espace, surveillance)
                executees += 1
                if verdict.notifier:
                    logger.info("Surveillance « %s » : %s", surveillance.titre, verdict.message)
            except Exception:  # noqa: BLE001
                logger.exception("Surveillance « %s » a echoue", surveillance.titre)
    logger.info("Tour de %s h : %s surveillance(s) executee(s)", heure, executees)
    return executees
