"""Creer et relire les notifications, et savoir a qui les adresser.

Une notification d'espace va a tous ceux qui peuvent l'ouvrir : ses acces
explicites et les admins de l'organisation. Creer ne commite pas, comme
l'audit : la notification suit la transaction de l'evenement qu'elle annonce.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.membership import ROLES_ADMIN_ORGANISATION, Membership
from app.models.notification import Notification
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_access import WorkspaceAccess

LISTE_MAX = 50


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def creer(
        self, user_id: str, type_: str, titre: str, corps: str = "", lien: str | None = None
    ) -> Notification:
        notification = Notification(
            user_id=user_id, type=type_, titre=titre[:160], corps=corps, lien=lien
        )
        self._db.add(notification)
        return notification

    async def notifier_espace(
        self, espace: Workspace, type_: str, titre: str, corps: str = "", lien: str | None = None
    ) -> list[Notification]:
        return [
            self.creer(user_id, type_, titre, corps, lien)
            for user_id in await self._destinataires_espace(espace)
        ]

    async def notifier_admins(
        self, organisation_id: str, type_: str, titre: str, corps: str = "", lien: str | None = None
    ) -> list[Notification]:
        return [
            self.creer(user_id, type_, titre, corps, lien)
            for user_id in await self._admins(organisation_id)
        ]

    async def lister(self, utilisateur: User) -> list[Notification]:
        resultat = await self._db.execute(
            select(Notification)
            .where(Notification.user_id == utilisateur.id)
            .order_by(Notification.cree_le.desc())
            .limit(LISTE_MAX)
        )
        return list(resultat.scalars())

    async def nb_non_lues(self, utilisateur: User) -> int:
        nb = await self._db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == utilisateur.id, Notification.lue.is_(False)
            )
        )
        return int(nb or 0)

    async def marquer_lue(self, utilisateur: User, notification_id: str) -> None:
        notification = await self._db.get(Notification, notification_id)
        if notification is None or notification.user_id != utilisateur.id:
            raise ErreurUtilisateur("Notification introuvable.", code_http=404)
        notification.lue = True
        await self._db.commit()

    async def tout_marquer_lu(self, utilisateur: User) -> None:
        resultat = await self._db.execute(
            select(Notification).where(
                Notification.user_id == utilisateur.id, Notification.lue.is_(False)
            )
        )
        for notification in resultat.scalars():
            notification.lue = True
        await self._db.commit()

    async def _destinataires_espace(self, espace: Workspace) -> set[str]:
        acces = await self._db.execute(
            select(WorkspaceAccess.user_id).where(WorkspaceAccess.workspace_id == espace.id)
        )
        return set(acces.scalars()) | await self._admins(espace.organization_id)

    async def _admins(self, organisation_id: str) -> set[str]:
        resultat = await self._db.execute(
            select(Membership.user_id).where(
                Membership.organization_id == organisation_id,
                Membership.role.in_(ROLES_ADMIN_ORGANISATION),
            )
        )
        return set(resultat.scalars())
