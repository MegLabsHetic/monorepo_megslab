"""Une question qu'on ne pose plus : elle se pose toute seule, et previent.

L'agent ML sait deja lire une serie et y reperer une rupture de tendance ou un
point aberrant - mais seulement quand un humain declenche une question. Une
surveillance est la meme chose, declenchee par une horloge.

Elle ne stocke pas une question en francais mais **le SQL deja valide** qui en
est issu. Deux raisons : le declenchement ne coute alors aucun appel au modele,
et ce qui s'execute chaque matin est exactement ce que l'utilisateur a vu et
approuve le jour ou il a cree la surveillance.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace

TITRE_MAX = 120


class Declencheur(str, enum.Enum):
    """Ce qui fait qu'une execution merite une notification."""

    # L'agent ML signale un point aberrant ou une rupture de tendance.
    ANOMALIE = "anomalie"
    # La premiere valeur de la premiere ligne depasse le seuil.
    SEUIL_DEPASSE = "seuil_depasse"
    SEUIL_SOUS = "seuil_sous"
    # Notifier a chaque execution : un rapport, pas une alerte.
    TOUJOURS = "toujours"


class Surveillance(HorodatageMixin, Base):
    __tablename__ = "surveillances"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    titre: Mapped[str] = mapped_column(String(TITRE_MAX))
    # Le SQL tel qu'il a ete valide par le garde-fou au moment de la creation.
    # Il y repasse quand meme a chaque execution : ce qui etait vrai hier peut
    # ne plus l'etre, et le verifier ne coute rien.
    sql: Mapped[str] = mapped_column(Text)

    declencheur: Mapped[Declencheur] = mapped_column(
        Enum(Declencheur, native_enum=False, length=20), default=Declencheur.ANOMALIE
    )
    seuil: Mapped[float | None] = mapped_column(Float, default=None)

    # Heure locale d'execution, de 0 a 23. Une surveillance tourne une fois par
    # jour : plus souvent releverait du tableau de bord, pas de l'alerte.
    heure: Mapped[int] = mapped_column(default=8)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    derniere_execution: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    dernier_etat: Mapped[str] = mapped_column(Text, default="", server_default="")

    workspace: Mapped["Workspace"] = relationship()
    user: Mapped["User"] = relationship()
