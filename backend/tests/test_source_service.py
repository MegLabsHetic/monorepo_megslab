"""Connecter une source la decouvre ; synchroniser la relie a l'entrepot et lance un sync."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.models.data_source import StatutSource
from app.models.organization import Organization
from app.services.source_service import SourceService


async def _organisation(db: AsyncSession) -> Organization:
    organisation = Organization(
        nom="Espace de test",
        airbyte_workspace_id="workspace-test",
        airbyte_destination_id="destination-test",
    )
    db.add(organisation)
    await db.flush()
    return organisation


async def test_connecter_postgres_enregistre_la_source_et_renvoie_les_flux(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    organisation = await _organisation(db)
    service = SourceService(db, airbyte_client_factice)

    source, flux = await service.connecter_postgres(
        organisation, "Ma base", "hote", 5432, "base", "user", "mdp"
    )

    assert source.airbyte_source_id == "source-test"
    assert source.statut == StatutSource.CONNECTEE
    assert source.schema_entrepot == f"org_{organisation.id}"
    assert [f.nom for f in flux] == ["customers"]


async def test_synchroniser_cree_la_connexion_une_seule_fois(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    organisation = await _organisation(db)
    service = SourceService(db, airbyte_client_factice)
    source, _ = await service.connecter_postgres(
        organisation, "Ma base", "hote", 5432, "base", "user", "mdp"
    )

    job_id = await service.synchroniser(source, organisation, ["customers"])

    assert job_id == 1
    assert source.airbyte_connection_id == "connexion-test"
    assert source.statut == StatutSource.SYNCHRONISATION


async def test_statut_sync_marque_la_source_prete_quand_le_job_reussit(
    db: AsyncSession, airbyte_client_factice: AirbyteClient
) -> None:
    organisation = await _organisation(db)
    service = SourceService(db, airbyte_client_factice)
    source, _ = await service.connecter_postgres(
        organisation, "Ma base", "hote", 5432, "base", "user", "mdp"
    )
    await service.synchroniser(source, organisation, ["customers"])

    job = await service.statut_sync(source, 1)

    assert job["status"] == "succeeded"
    assert source.statut == StatutSource.PRETE
