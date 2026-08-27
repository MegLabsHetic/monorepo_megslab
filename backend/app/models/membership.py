"""L'appartenance d'un utilisateur a une organisation, avec son role.

Au niveau de l'organisation : OWNER (tout, y compris supprimer), ADMIN (gere
l'equipe et les espaces), MEMBER (accede aux espaces qu'on lui ouvre). Le
role VIEWER n'a de sens que dans un espace (voir `WorkspaceAccess`), l'enum
est partage entre les deux tables.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class Role(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLES_ORGANISATION = (Role.OWNER, Role.ADMIN, Role.MEMBER)
ROLES_ESPACE = (Role.ADMIN, Role.MEMBER, Role.VIEWER)
ROLES_ADMIN_ORGANISATION = (Role.OWNER, Role.ADMIN)


class Membership(HorodatageMixin, Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=20))

    user: Mapped["User"] = relationship(back_populates="memberships")
    organization: Mapped["Organization"] = relationship(back_populates="memberships")
