"""Une organisation : l'entreprise cliente.

Elle porte l'equipe (les appartenances et leurs roles), et plus tard la
facturation et le budget. Les donnees, elles, vivent dans ses espaces de
travail : c'est la que sont le workspace Airbyte et le schema d'entrepot.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.workspace import Workspace


class Organization(HorodatageMixin, Base):
    __tablename__ = "organizations"

    nom: Mapped[str] = mapped_column(String(255))
    # Le budget mensuel de l'assistant, en dollars ; nul = pas de limite.
    budget_mensuel_dollars: Mapped[float | None] = mapped_column(Float, default=None)
    seuil_alerte_pct: Mapped[int] = mapped_column(Integer, default=80, server_default="80")
    # Bloquant : une question de plus est refusee une fois le budget atteint.
    budget_bloquant: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    memberships: Mapped[list["Membership"]] = relationship(back_populates="organization")
    workspaces: Mapped[list["Workspace"]] = relationship(back_populates="organization")
