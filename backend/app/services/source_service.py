"""Connexion d'une source de donnees et declenchement de sa synchronisation."""

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient, StreamDecouvert
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource, StatutSource
from app.models.organization import Organization

logger = logging.getLogger(__name__)

_ERREUR_AIRBYTE_INJOIGNABLE = (
    "Le service de connexion aux sources de donnees est momentanement indisponible."
)


class SourceService:
    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient) -> None:
        self._db = db
        self._airbyte_client = airbyte_client

    async def connecter_postgres(
        self,
        organisation: Organization,
        nom: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
    ) -> tuple[DataSource, list[StreamDecouvert]]:
        """Cree la source cote Airbyte, decouvre ses tables, et l'enregistre.

        La connexion (qui relie cette source a l'entrepot) n'est creee qu'a
        `synchroniser` : entre les deux, l'utilisateur choisit quelles tables
        l'interessent.
        """
        try:
            source_id = await self._airbyte_client.creer_source_postgres(
                workspace_id=organisation.airbyte_workspace_id,
                nom=nom,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
            )
            flux = await self._airbyte_client.lister_streams(source_id)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de connexion/decouverte Airbyte pour la source %s", nom)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        source = DataSource(
            organization_id=organisation.id,
            nom=nom,
            airbyte_source_id=source_id,
            schema_entrepot=f"org_{organisation.id}",
            flux_decouverts=[
                {"nom": f.nom, "namespace": f.namespace, "colonnes": f.colonnes} for f in flux
            ],
        )
        self._db.add(source)
        await self._db.commit()
        await self._db.refresh(source)
        return source, flux

    async def synchroniser(
        self, source: DataSource, organisation: Organization, noms_flux: list[str]
    ) -> int:
        """Relie la source a l'entrepot de l'organisation et lance un sync.

        Renvoie l'id du job Airbyte : le suivi de sa progression se fait a part
        (`statut_sync`), pour ne jamais faire attendre une requete HTTP le
        temps complet d'une synchronisation.
        """
        try:
            if source.airbyte_connection_id is None:
                source.airbyte_connection_id = await self._airbyte_client.creer_connexion(
                    source.airbyte_source_id,
                    organisation.airbyte_destination_id,
                    f"{source.nom} -> entrepot",
                )
            await self._airbyte_client.selectionner_streams(source.airbyte_connection_id, noms_flux)
            job_id = await self._airbyte_client.declencher_sync(source.airbyte_connection_id)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de synchronisation Airbyte pour la source %s", source.id)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        source.statut = StatutSource.SYNCHRONISATION
        source.flux_selectionnes = noms_flux
        await self._db.commit()
        return job_id

    async def lister(self, organisation: Organization) -> list[DataSource]:
        """Les sources connectees par une organisation, la plus recente d'abord."""
        resultat = await self._db.execute(
            select(DataSource)
            .where(DataSource.organization_id == organisation.id)
            .order_by(DataSource.cree_le.desc())
        )
        return list(resultat.scalars().all())

    async def statut_sync(self, source: DataSource, job_id: int) -> dict:
        """Interroge Airbyte pour l'etat d'un job, et met a jour la source si termine."""
        try:
            job = await self._airbyte_client.obtenir_job(job_id)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de lecture du statut du job Airbyte %s", job_id)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        if job.get("status") == "succeeded":
            source.statut = StatutSource.PRETE
            await self._db.commit()
        elif job.get("status") in ("failed", "cancelled", "incomplete"):
            source.statut = StatutSource.ERREUR
            await self._db.commit()
        return job
