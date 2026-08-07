"""Creation d'organisations et rattachement de leurs membres."""

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User

logger = logging.getLogger(__name__)

_ERREUR_AIRBYTE_INJOIGNABLE = (
    "Le service de connexion aux sources de donnees est momentanement "
    "indisponible. Reessayez dans un instant."
)


class OrganizationService:
    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient) -> None:
        self._db = db
        self._airbyte_client = airbyte_client

    async def creer_avec_proprietaire(self, nom: str, proprietaire: User) -> Organization:
        """Cree une organisation, son workspace Airbyte, sa part de l'entrepot
        partage, et rattache son createur comme OWNER.

        Choix assume : sans workspace ni entrepot, une organisation ne peut rien
        connecter. On refuse donc de la creer si Airbyte ne repond pas plutot
        que de laisser une organisation a moitie provisionnee. Ne commite pas :
        l'appelant (l'inscription) gere la transaction.
        """
        workspace_id = await self._creer_workspace(nom)

        organisation = Organization(nom=nom, airbyte_workspace_id=workspace_id)
        self._db.add(organisation)
        await self._db.flush()  # attribue l'id de l'organisation, necessaire au nom du schema

        organisation.airbyte_destination_id = await self._creer_destination(
            workspace_id, organisation.id
        )

        self._db.add(
            Membership(user_id=proprietaire.id, organization_id=organisation.id, role=Role.OWNER)
        )
        return organisation

    async def _creer_workspace(self, nom: str) -> str:
        try:
            return await self._airbyte_client.creer_workspace(nom)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de creation du workspace Airbyte pour %s", nom)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

    async def _creer_destination(self, workspace_id: str, organization_id: str) -> str:
        reglages = get_settings()
        try:
            return await self._airbyte_client.creer_destination_postgres(
                workspace_id=workspace_id,
                nom="Entrepot",
                host=reglages.warehouse_postgres_host,
                port=reglages.warehouse_postgres_port,
                database=reglages.warehouse_postgres_database,
                username=reglages.warehouse_postgres_username,
                password=reglages.warehouse_postgres_password,
                schema=f"org_{organization_id}",
            )
        except httpx.HTTPError as erreur:
            logger.exception("Echec de creation de la destination Airbyte pour %s", organization_id)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur
