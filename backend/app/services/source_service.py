"""Connexion d'une source de donnees et declenchement de sa synchronisation."""

import asyncio
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.data import AgentData
from app.core.airbyte_client import AirbyteClient, SourceAirbyte, StreamDecouvert
from app.core.connecteurs import connecteur
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource, StatutSource
from app.models.organization import Organization

logger = logging.getLogger(__name__)

# Airbyte garde brievement un verrou sur la connexion apres la selection des
# flux : deux secondes suffisent en pratique a le voir se relacher.
TENTATIVES_DECLENCHEMENT = 3
DELAI_ENTRE_TENTATIVES_SECONDES = 2

_ERREUR_AIRBYTE_INJOIGNABLE = (
    "Le service de connexion aux sources de donnees est momentanement indisponible."
)


class SourceService:
    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient) -> None:
        self._db = db
        self._airbyte_client = airbyte_client

    async def connecter_base(
        self,
        organisation: Organization,
        type_source: str,
        nom: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
    ) -> tuple[DataSource, list[StreamDecouvert]]:
        """Cree la source cote Airbyte, decouvre ses tables, et l'enregistre.

        `type_source` choisit le connecteur (PostgreSQL, MySQL, SQL Server) :
        seule la configuration envoyee a Airbyte change, le reste du parcours
        est identique.

        La connexion (qui relie cette source a l'entrepot) n'est creee qu'a
        `synchroniser` : entre les deux, l'utilisateur choisit quelles tables
        l'interessent.
        """
        try:
            configuration = connecteur(type_source).configuration(
                host, port, database, username, password
            )
            source_id = await self._airbyte_client.creer_source(
                organisation.airbyte_workspace_id, nom, configuration
            )
            flux = await self._airbyte_client.lister_streams(source_id)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de connexion/decouverte Airbyte pour la source %s", nom)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        source = DataSource(
            organization_id=organisation.id,
            nom=nom,
            type_source=type_source,
            airbyte_source_id=source_id,
            schema_entrepot=f"org_{organisation.id}",
            # Court, stable, et derive de l'id Airbyte : deux sources d'une meme
            # organisation ne peuvent pas produire le meme prefixe.
            prefixe_entrepot=f"s{source_id.replace('-', '')[:8]}_",
            flux_decouverts=[
                {"nom": f.nom, "namespace": f.namespace, "colonnes": f.colonnes} for f in flux
            ],
        )
        self._db.add(source)
        await self._db.commit()
        await self._db.refresh(source)
        return source, flux

    async def sources_airbyte_importables(self, organisation: Organization) -> list[SourceAirbyte]:
        """Les sources presentes dans le workspace Airbyte mais inconnues de MegLabs.

        Typiquement : celles configurees directement dans Airbyte, pour un
        connecteur que notre formulaire ne propose pas.
        """
        try:
            toutes = await self._airbyte_client.lister_sources(organisation.airbyte_workspace_id)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de listage des sources Airbyte de %s", organisation.id)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        connues = {source.airbyte_source_id for source in await self.lister(organisation)}
        return [source for source in toutes if source.id not in connues]

    async def importer_depuis_airbyte(
        self, organisation: Organization, airbyte_source_id: str
    ) -> DataSource:
        """Adopte une source existante d'Airbyte : MegLabs la reference et la gere ensuite.

        Aucun identifiant n'est demande : ils sont deja chez Airbyte, chiffres.
        On ne fait que decouvrir son schema et l'enregistrer.
        """
        importables = await self.sources_airbyte_importables(organisation)
        correspondance = next((s for s in importables if s.id == airbyte_source_id), None)
        if correspondance is None:
            raise ErreurUtilisateur(
                "Cette source n'existe pas dans votre espace, ou est deja importee.",
                code_http=404,
            )

        try:
            flux = await self._airbyte_client.lister_streams(airbyte_source_id)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de decouverte de la source adoptee %s", airbyte_source_id)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        source = DataSource(
            organization_id=organisation.id,
            nom=correspondance.nom,
            type_source=correspondance.type_source,
            airbyte_source_id=correspondance.id,
            schema_entrepot=f"org_{organisation.id}",
            prefixe_entrepot=f"s{correspondance.id.replace('-', '')[:8]}_",
            flux_decouverts=[
                {"nom": f.nom, "namespace": f.namespace, "colonnes": f.colonnes} for f in flux
            ],
        )
        self._db.add(source)
        await self._db.commit()
        await self._db.refresh(source)
        logger.info("Source Airbyte %s adoptee par %s", airbyte_source_id, organisation.id)
        return source

    async def synchroniser(
        self, source: DataSource, organisation: Organization, noms_flux: list[str]
    ) -> int:
        """Relie la source a l'entrepot de l'organisation et lance un sync.

        Renvoie l'id du job Airbyte : le suivi de sa progression se fait a part
        (`statut_sync`), pour ne jamais faire attendre une requete HTTP le
        temps complet d'une synchronisation.
        """
        await self._garantir_connexion(source, organisation)

        try:
            await self._airbyte_client.selectionner_streams(source.airbyte_connection_id, noms_flux)
            job_id = await self._declencher_ou_recuperer(source.airbyte_connection_id)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de synchronisation Airbyte pour la source %s", source.id)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        source.statut = StatutSource.SYNCHRONISATION
        source.flux_selectionnes = noms_flux
        await self._db.commit()
        return job_id

    async def _garantir_connexion(self, source: DataSource, organisation: Organization) -> None:
        """Cree la connexion si elle manque, et l'enregistre aussitot.

        Le commit immediat n'est pas cosmetique : si le declenchement echoue
        juste apres, la connexion existe deja cote Airbyte. Sans cet
        enregistrement, chaque nouvelle tentative en creerait une autre,
        orpheline, que plus personne ne pourrait retrouver.
        """
        if source.airbyte_connection_id is not None:
            return

        try:
            source.airbyte_connection_id = await self._airbyte_client.creer_connexion(
                source.airbyte_source_id,
                organisation.airbyte_destination_id,
                f"{source.nom} -> entrepot",
                prefixe=source.prefixe_entrepot,
            )
        except httpx.HTTPError as erreur:
            logger.exception("Echec de creation de la connexion pour la source %s", source.id)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

        await self._db.commit()

    async def _declencher_ou_recuperer(self, connection_id: str) -> int:
        """Lance une synchronisation, en absorbant les deux causes de 409.

        Airbyte repond 409 dans deux situations differentes, constatees en
        pratique :

        - une synchronisation tourne vraiment (il en declenche parfois une
          lui-meme a la selection des flux) : la suivre vaut mieux qu'echouer ;
        - le verrou pose sur la connexion juste apres la selection des flux
          n'est pas encore relache. C'est transitoire, et la liste des jobs est
          alors vide — d'ou une nouvelle tentative apres une courte pause.
        """
        for tentative in range(TENTATIVES_DECLENCHEMENT):
            try:
                return await self._airbyte_client.declencher_sync(connection_id)
            except httpx.HTTPStatusError as erreur:
                if erreur.response.status_code != 409:
                    raise

                job_id = await self._airbyte_client.job_en_cours(connection_id)
                if job_id is not None:
                    logger.info("Synchronisation deja en cours (job %s), on la suit", job_id)
                    return job_id

                if tentative == TENTATIVES_DECLENCHEMENT - 1:
                    raise
                logger.info("Connexion encore verrouillee, nouvelle tentative")
                await asyncio.sleep(DELAI_ENTRE_TENTATIVES_SECONDES)

        raise RuntimeError("boucle de declenchement terminee sans resultat")

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
            # L'entrepot vient de changer : le contexte que l'assistant garde
            # en memoire ne le decrit plus.
            AgentData.oublier(source.schema_entrepot)
        elif job.get("status") in ("failed", "cancelled", "incomplete"):
            source.statut = StatutSource.ERREUR
            await self._db.commit()
        return job
