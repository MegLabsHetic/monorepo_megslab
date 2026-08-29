"""Creation et administration des espaces de travail."""

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur
from app.models.membership import ROLES_ESPACE, Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_access import WorkspaceAccess

logger = logging.getLogger(__name__)

_ERREUR_AIRBYTE_INJOIGNABLE = (
    "Le service de connexion aux sources de donnees est momentanement "
    "indisponible. Reessayez dans un instant."
)


class WorkspaceService:
    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient) -> None:
        self._db = db
        self._airbyte_client = airbyte_client

    async def creer(self, organisation: Organization, nom: str, createur: User) -> Workspace:
        """Un nouvel espace, provisionne, avec son createur en ADMIN. Commite."""
        espace = await self.preparer(organisation, nom)
        self._db.add(WorkspaceAccess(workspace_id=espace.id, user_id=createur.id, role=Role.ADMIN))
        await self._db.commit()
        await self._db.refresh(espace)
        return espace

    async def preparer(self, organisation: Organization, nom: str) -> Workspace:
        """Cree l'espace et sa plomberie Airbyte, sans commiter.

        Choix assume : sans workspace Airbyte ni schema d'entrepot, un espace ne
        peut rien connecter. On refuse donc de le creer si Airbyte ne repond
        pas plutot que de laisser un espace a moitie provisionne. L'appelant
        tient la transaction : l'inscription cree organisation et premier
        espace d'un seul tenant.
        """
        workspace_id = await self._creer_workspace_airbyte(f"{organisation.nom} / {nom}")
        espace = Workspace(
            organization_id=organisation.id,
            nom=nom,
            airbyte_workspace_id=workspace_id,
            schema_entrepot="",
        )
        self._db.add(espace)
        await self._db.flush()  # attribue l'id, dont le nom du schema depend
        espace.schema_entrepot = f"ws_{espace.id}"
        espace.airbyte_destination_id = await self._creer_destination(
            workspace_id, espace.schema_entrepot
        )
        return espace

    async def renommer(self, espace: Workspace, nom: str) -> Workspace:
        espace.nom = nom.strip()
        await self._db.commit()
        await self._db.refresh(espace)
        return espace

    async def acces(self, espace: Workspace) -> list[tuple[User, Role]]:
        """Les acces explicites a l'espace. Les admins de l'organisation n'y
        figurent pas : leur acces est herite, pas accorde."""
        resultat = await self._db.execute(
            select(User, WorkspaceAccess.role)
            .join(WorkspaceAccess, WorkspaceAccess.user_id == User.id)
            .where(WorkspaceAccess.workspace_id == espace.id)
            .order_by(User.nom_complet)
        )
        return [(utilisateur, role) for utilisateur, role in resultat.all()]

    async def definir_acces(self, espace: Workspace, utilisateur: User, role: Role | None) -> None:
        """Donne, change ou retire (`None`) l'acces d'un membre a l'espace."""
        if role is not None and role not in ROLES_ESPACE:
            raise ErreurUtilisateur("Ce role n'existe pas dans un espace.", code_http=422)
        existant = (
            await self._db.execute(
                select(WorkspaceAccess).where(
                    WorkspaceAccess.workspace_id == espace.id,
                    WorkspaceAccess.user_id == utilisateur.id,
                )
            )
        ).scalar_one_or_none()

        if role is None:
            if existant is not None:
                await self._db.delete(existant)
        elif existant is None:
            self._db.add(WorkspaceAccess(workspace_id=espace.id, user_id=utilisateur.id, role=role))
        else:
            existant.role = role
        await self._db.commit()

    async def _creer_workspace_airbyte(self, nom: str) -> str:
        try:
            return await self._airbyte_client.creer_workspace(nom)
        except httpx.HTTPError as erreur:
            logger.exception("Echec de creation du workspace Airbyte pour %s", nom)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur

    async def _creer_destination(self, workspace_id: str, schema: str) -> str:
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
                schema=schema,
            )
        except httpx.HTTPError as erreur:
            logger.exception("Echec de creation de la destination Airbyte pour %s", schema)
            raise ErreurUtilisateur(_ERREUR_AIRBYTE_INJOIGNABLE, code_http=503) from erreur
