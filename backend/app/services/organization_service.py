"""Creation d'organisations et rattachement de leurs membres."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace_access import WorkspaceAccess
from app.services.workspace_service import WorkspaceService

NOM_PREMIER_ESPACE = "General"


class OrganizationService:
    def __init__(self, db: AsyncSession, airbyte_client: AirbyteClient) -> None:
        self._db = db
        self._airbyte_client = airbyte_client

    async def creer_avec_proprietaire(self, nom: str, proprietaire: User) -> Organization:
        """Cree une organisation, son premier espace provisionne, et rattache
        son createur comme OWNER.

        Ne commite pas : l'appelant (l'inscription) gere la transaction, pour
        que compte, organisation et espace naissent ensemble ou pas du tout.
        """
        organisation = Organization(nom=nom)
        self._db.add(organisation)
        await self._db.flush()  # attribue l'id, necessaire a l'espace

        espace = await WorkspaceService(self._db, self._airbyte_client).preparer(
            organisation, NOM_PREMIER_ESPACE
        )
        self._db.add_all(
            [
                Membership(
                    user_id=proprietaire.id, organization_id=organisation.id, role=Role.OWNER
                ),
                # Implicite pour un OWNER, mais explicite ici : la page Equipe
                # montre alors qui a acces a quoi sans cas particulier.
                WorkspaceAccess(workspace_id=espace.id, user_id=proprietaire.id, role=Role.ADMIN),
            ]
        )
        return organisation

    async def renommer(self, organisation: Organization, nom: str) -> Organization:
        organisation.nom = nom.strip()
        await self._db.commit()
        await self._db.refresh(organisation)
        return organisation
