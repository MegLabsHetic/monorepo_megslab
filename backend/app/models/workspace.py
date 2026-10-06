"""Un espace de travail : une equipe ou un projet dans une organisation.

C'est l'espace, pas l'organisation, qui isole les donnees. Chaque espace a
son workspace Airbyte (les identifiants de connexion d'une equipe ne sont
jamais visibles d'une autre) et son schema dans l'entrepot partage (une seule
base Postgres, un schema par espace). L'organisation porte l'equipe, la
facturation et le budget ; l'espace porte les sources, les conversations et
les tableaux de bord.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.workspace_access import WorkspaceAccess


class Workspace(HorodatageMixin, Base):
    __tablename__ = "workspaces"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    nom: Mapped[str] = mapped_column(String(255))
    airbyte_workspace_id: Mapped[str | None] = mapped_column(String(64), default=None)
    airbyte_destination_id: Mapped[str | None] = mapped_column(String(64), default=None)
    # « org_<id> » pour les espaces herites d'avant les espaces, « ws_<id> » ensuite.
    schema_entrepot: Mapped[str] = mapped_column(String(64))

    organization: Mapped["Organization"] = relationship(back_populates="workspaces")
    acces: Mapped[list["WorkspaceAccess"]] = relationship(back_populates="workspace")
