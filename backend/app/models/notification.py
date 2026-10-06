"""Une notification dans l'application, adressee a un utilisateur.

Pas d'e-mail : la cloche de l'interface les montre, et l'utilisateur les
marque lues. Chaque notification porte un lien vers ce dont elle parle.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.user import User


class Notification(HorodatageMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    # « sync », « budget », « equipe »... : l'interface choisit l'icone d'apres lui.
    type: Mapped[str] = mapped_column(String(30))
    titre: Mapped[str] = mapped_column(String(160))
    corps: Mapped[str] = mapped_column(Text, default="")
    lien: Mapped[str | None] = mapped_column(String(255), default=None)
    lue: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    user: Mapped["User"] = relationship()
