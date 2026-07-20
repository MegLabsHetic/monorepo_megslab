"""Creation d'organisations et rattachement de leurs membres."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def creer_avec_proprietaire(self, nom: str, proprietaire: User) -> Organization:
        """Cree une organisation et y rattache son createur comme OWNER.

        Ne commite pas : appelee depuis l'inscription, qui doit rester une seule
        transaction (utilisateur + organisation + membership, tout ou rien).
        """
        organisation = Organization(nom=nom)
        self._db.add(organisation)
        await self._db.flush()  # attribue l'id de l'organisation sans cloturer la transaction

        self._db.add(
            Membership(user_id=proprietaire.id, organization_id=organisation.id, role=Role.OWNER)
        )
        return organisation
