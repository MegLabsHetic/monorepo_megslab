"""Qui a le droit de faire quoi, et ou.

Un seul endroit repond a ces questions, pour que les routes n'aient qu'a
demander. Deux niveaux : le role dans l'organisation (appartenance), et le
role dans un espace (acces). Les proprietaires et admins de l'organisation
sont implicitement ADMIN de chacun de ses espaces.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import ROLES_ADMIN_ORGANISATION, Membership, Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_access import WorkspaceAccess


class AccesService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def role_organisation(self, utilisateur: User, organisation: Organization) -> Role | None:
        resultat = await self._db.execute(
            select(Membership.role).where(
                Membership.user_id == utilisateur.id,
                Membership.organization_id == organisation.id,
            )
        )
        return resultat.scalar_one_or_none()

    async def est_admin_organisation(self, utilisateur: User, organisation: Organization) -> bool:
        return await self.role_organisation(utilisateur, organisation) in ROLES_ADMIN_ORGANISATION

    async def role_espace(self, utilisateur: User, espace: Workspace) -> Role | None:
        """Le role effectif dans l'espace : explicite, ou herite de l'organisation."""
        organisation = await self._db.get(Organization, espace.organization_id)
        if organisation is not None and await self.est_admin_organisation(
            utilisateur, organisation
        ):
            return Role.ADMIN
        resultat = await self._db.execute(
            select(WorkspaceAccess.role).where(
                WorkspaceAccess.user_id == utilisateur.id,
                WorkspaceAccess.workspace_id == espace.id,
            )
        )
        return resultat.scalar_one_or_none()

    async def espaces_accessibles(
        self, utilisateur: User, organisation: Organization
    ) -> list[tuple[Workspace, Role]]:
        """Les espaces de l'organisation que l'utilisateur peut ouvrir, avec son role."""
        espaces = list(
            (
                await self._db.execute(
                    select(Workspace)
                    .where(Workspace.organization_id == organisation.id)
                    .order_by(Workspace.cree_le)
                )
            ).scalars()
        )
        if await self.est_admin_organisation(utilisateur, organisation):
            return [(espace, Role.ADMIN) for espace in espaces]

        acces = await self._db.execute(
            select(WorkspaceAccess.workspace_id, WorkspaceAccess.role).where(
                WorkspaceAccess.user_id == utilisateur.id,
                WorkspaceAccess.workspace_id.in_([e.id for e in espaces]),
            )
        )
        roles = dict(acces.all())
        return [(espace, roles[espace.id]) for espace in espaces if espace.id in roles]

    async def organisation_de(self, utilisateur: User) -> Organization | None:
        """L'organisation de l'utilisateur.

        Simplification assumee : un utilisateur n'appartient qu'a une
        organisation pour l'instant. Le multi-organisation viendra avec un
        vrai selecteur cote interface.
        """
        resultat = await self._db.execute(
            select(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == utilisateur.id)
            .order_by(Membership.cree_le)
            .limit(1)
        )
        return resultat.scalar_one_or_none()
