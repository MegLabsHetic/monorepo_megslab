"""La console de l'operateur : toutes les organisations, la sante du systeme.

Reservee aux super-admins. Rien ici n'est cache aux organisations elles-memes :
ce sont leurs propres compteurs, vus d'en haut.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import super_admin
from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.database import get_db
from app.schemas.plateforme import (
    ComposantSanteReponse,
    OrganisationPlateformeReponse,
    SanteReponse,
)
from app.services.platform_service import PlatformService

router = APIRouter(prefix="/plateforme", tags=["plateforme"], dependencies=[Depends(super_admin)])


@router.get("/organisations", response_model=list[OrganisationPlateformeReponse])
async def organisations(db: AsyncSession = Depends(get_db)):
    return [
        OrganisationPlateformeReponse(
            id=o.organisation.id,
            nom=o.organisation.nom,
            cree_le=o.organisation.cree_le,
            nb_membres=o.nb_membres,
            nb_espaces=o.nb_espaces,
            nb_sources=o.nb_sources,
            nb_questions=o.nb_questions,
            cout_dollars=o.cout_dollars,
        )
        for o in await PlatformService(db).organisations()
    ]


@router.get("/sante", response_model=SanteReponse)
async def sante(
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    """Chaque dependance est reellement eprouvee, pas seulement configuree."""
    service = PlatformService(db)
    composants = await service.sante(airbyte_client)
    totaux = await service.totaux()
    return SanteReponse(
        composants=[
            ComposantSanteReponse(nom=c.nom, etat=c.etat, detail=c.detail, latence_ms=c.latence_ms)
            for c in composants
        ],
        nb_organisations=totaux.nb_organisations,
        nb_utilisateurs=totaux.nb_utilisateurs,
        cout_total_dollars=totaux.cout_dollars,
    )
