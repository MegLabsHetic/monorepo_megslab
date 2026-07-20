"""Un compte utilisateur."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.membership import Membership


class User(HorodatageMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    # Nullable : un compte cree uniquement via Google/Microsoft n'a pas de mot de passe.
    mot_de_passe_hache: Mapped[str | None] = mapped_column(String(255), default=None)
    nom_complet: Mapped[str] = mapped_column(String(255))
    actif: Mapped[bool] = mapped_column(Boolean, default=True)

    memberships: Mapped[list["Membership"]] = relationship(back_populates="user")
