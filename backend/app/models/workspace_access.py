"""L'acces d'un utilisateur a un espace de travail, avec son role dans cet espace.

Trois roles : ADMIN gere les sources et les acces, MEMBER interroge et
construit, VIEWER consulte sans rien depenser. Les proprietaires et admins de
l'organisation ont implicitement l'acces ADMIN a tous ses espaces : ce n'est
pas stocke ici, c'est `AccesService` qui le sait.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin
from app.models.membership import Role

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace


class WorkspaceAccess(HorodatageMixin, Base):
    __tablename__ = "workspace_accesses"
    __table_args__ = (UniqueConstraint("user_id", "workspace_id"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=20))

    user: Mapped["User"] = relationship()
    workspace: Mapped["Workspace"] = relationship(back_populates="acces")
