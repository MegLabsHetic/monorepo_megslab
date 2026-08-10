"""Routes de connexion et de synchronisation des sources de donnees."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import organisation_courante
from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource
from app.models.organization import Organization
from app.schemas.source import (
    ConnexionPostgresDemande,
    FluxReponse,
    SourceReponse,
    StatutSyncReponse,
    SynchronisationDemande,
    SynchronisationReponse,
)
from app.services.source_service import SourceService

router = APIRouter(prefix="/sources", tags=["sources"])


@router.post("", response_model=SourceReponse, status_code=201)
async def connecter(
    demande: ConnexionPostgresDemande,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    service = SourceService(db, airbyte_client)
    source, flux = await service.connecter_postgres(
        organisation,
        demande.nom,
        demande.host,
        demande.port,
        demande.database,
        demande.username,
        demande.mot_de_passe,
    )
    return SourceReponse(
        id=source.id,
        nom=source.nom,
        statut=source.statut.value,
        flux_disponibles=[
            FluxReponse(nom=f.nom, namespace=f.namespace, colonnes=f.colonnes) for f in flux
        ],
    )


@router.post("/{source_id}/synchroniser", response_model=SynchronisationReponse)
async def synchroniser(
    source_id: str,
    demande: SynchronisationDemande,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source = await _charger_source(db, source_id, organisation)
    service = SourceService(db, airbyte_client)
    job_id = await service.synchroniser(source, organisation, demande.flux)
    return SynchronisationReponse(job_id=job_id)


@router.get("/{source_id}/synchronisation/{job_id}", response_model=StatutSyncReponse)
async def statut_synchronisation(
    source_id: str,
    job_id: int,
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    source = await _charger_source(db, source_id, organisation)
    service = SourceService(db, airbyte_client)
    job = await service.statut_sync(source, job_id)
    return StatutSyncReponse(
        statut=job.get("status", "inconnu"), lignes_synchronisees=job.get("rowsSynced")
    )


async def _charger_source(
    db: AsyncSession, source_id: str, organisation: Organization
) -> DataSource:
    source = await db.get(DataSource, source_id)
    if source is None or source.organization_id != organisation.id:
        raise ErreurUtilisateur("Source introuvable.", code_http=404)
    return source
