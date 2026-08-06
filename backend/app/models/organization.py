"""Une organisation : la frontiere qui isole les donnees d'une equipe.

`airbyte_workspace_id` fait le lien avec le workspace Airbyte cree pour cette
organisation (une organisation = un workspace, pour que les identifiants de
connexion d'une equipe ne soient jamais visibles d'une autre).

`airbyte_destination_id` pointe vers l'entrepot partage (une seule base
Postgres pour toutes les organisations), mais dans le schema propre a cette
organisation : l'isolation des donnees se fait par schema, pas par serveur.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.membership import Membership


class Organization(HorodatageMixin, Base):
    __tablename__ = "organizations"

    nom: Mapped[str] = mapped_column(String(255))
    airbyte_workspace_id: Mapped[str | None] = mapped_column(String(64), default=None)
    airbyte_destination_id: Mapped[str | None] = mapped_column(String(64), default=None)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
