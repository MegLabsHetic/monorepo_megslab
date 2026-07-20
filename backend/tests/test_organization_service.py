"""La creation d'une organisation rattache son createur comme OWNER."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, Role
from app.models.user import User
from app.services.organization_service import OrganizationService


async def test_le_createur_devient_owner_de_l_organisation(db: AsyncSession) -> None:
    utilisateur = User(email="ada@example.com", nom_complet="Ada")
    db.add(utilisateur)
    await db.flush()

    organisation = await OrganizationService(db).creer_avec_proprietaire(
        nom="Espace de Ada", proprietaire=utilisateur
    )
    await db.commit()

    resultat = await db.execute(
        select(Membership).where(Membership.organization_id == organisation.id)
    )
    membership = resultat.scalar_one()
    assert membership.user_id == utilisateur.id
    assert membership.role == Role.OWNER
