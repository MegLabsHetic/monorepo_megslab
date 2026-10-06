"""Le journal d'audit : qui a fait quoi, sur quoi, quand.

Une ligne par action qui change quelque chose ou coute quelque chose. On
n'enregistre jamais de secret ni de donnee metier, seulement de quoi
retrouver l'action : son type, sa cible et un detail court.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(HorodatageMixin, Base):
    __tablename__ = "audit_logs"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    workspace_id: Mapped[str | None] = mapped_column(ForeignKey("workspaces.id"), default=None)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    # « source.connectee », « question.posee », « membre.invite »...
    action: Mapped[str] = mapped_column(String(60), index=True)
    cible_type: Mapped[str] = mapped_column(String(40))
    cible_id: Mapped[str | None] = mapped_column(String(64), default=None)
    cible_nom: Mapped[str] = mapped_column(String(255), default="")
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

    user: Mapped["User"] = relationship()
