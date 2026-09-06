"""Un tableau de bord : des reponses epinglees, rejouees a chaque ouverture.

Un widget garde le SQL et le graphique d'une reponse, pas son resultat : a
l'ouverture du tableau, chaque requete est re-executee sur l'entrepot, apres
le meme garde-fou qu'a l'origine. Ce qu'on voit est donc toujours l'etat
actuel des donnees, jamais une capture d'ecran.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace

NOM_MAX = 120


class Dashboard(HorodatageMixin, Base):
    __tablename__ = "dashboards"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    nom: Mapped[str] = mapped_column(String(NOM_MAX))

    workspace: Mapped["Workspace"] = relationship()
    user: Mapped["User"] = relationship()
    widgets: Mapped[list["Widget"]] = relationship(
        back_populates="dashboard", order_by="Widget.position"
    )


class Widget(HorodatageMixin, Base):
    __tablename__ = "widgets"

    dashboard_id: Mapped[str] = mapped_column(ForeignKey("dashboards.id"), index=True)
    # La question d'origine, si elle existe encore : pour retrouver le fil.
    question_id: Mapped[str | None] = mapped_column(ForeignKey("questions.id"), default=None)
    titre: Mapped[str] = mapped_column(String(NOM_MAX))
    # Le SQL tel qu'il a ete valide et regenere par le garde-fou.
    sql: Mapped[str] = mapped_column(Text)
    # La specification du graphique choisie par l'agent Viz, ou nulle : tableau.
    graphique: Mapped[dict | None] = mapped_column(JSON, default=None)
    position: Mapped[int] = mapped_column(Integer, default=0)

    dashboard: Mapped["Dashboard"] = relationship(back_populates="widgets")
