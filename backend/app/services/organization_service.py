"""Creation d'organisations et rattachement de leurs membres."""

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.core.errors import ErreurUtilisateur
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User


class OrganizationService:
    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient) -> None:
        self._db = db
        self._airbyte_client = airbyte_client

    async def creer_avec_proprietaire(self, nom: str, proprietaire: User) -> Organization:
        """Cree une organisation, son workspace Airbyte, et rattache son createur comme OWNER.

        Choix assume : sans workspace Airbyte, une organisation ne peut rien
        connecter. On refuse donc de la creer si Airbyte ne repond pas plutot
        que de laisser une organisation orpheline qu'il faudrait reparer plus
        tard. Ne commite pas : l'appelant (l'inscription) gere la transaction.
        """
        workspace_id = await self._provisionner_workspace(nom)

        organisation = Organization(nom=nom, airbyte_workspace_id=workspace_id)
        self._db.add(organisation)
        await self._db.flush()  # attribue l'id de l'organisation sans cloturer la transaction

        self._db.add(
            Membership(user_id=proprietaire.id, organization_id=organisation.id, role=Role.OWNER)
        )
        return organisation

    async def _provisionner_workspace(self, nom: str) -> str:
        try:
            return await self._airbyte_client.creer_workspace(nom)
        except httpx.HTTPError as erreur:
            raise ErreurUtilisateur(
                "Le service de connexion aux sources de donnees est momentanement "
                "indisponible. Reessayez dans un instant.",
                code_http=503,
            ) from erreur
