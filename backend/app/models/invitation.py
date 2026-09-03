"""Une invitation a rejoindre une organisation, portee par un jeton a usage unique.

Aucun e-mail n'est envoye : l'admin recupere le lien et le transmet lui-meme.
Le jeton est aleatoire et long ; il n'est valable que jusqu'a `expire_le` et
ne sert qu'une fois.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin
from app.models.membership import Role

if TYPE_CHECKING:
    from app.models.organization import Organization


class Invitation(HorodatageMixin, Base):
    __tablename__ = "invitations"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role, native_enum=False, length=20))
    # Les espaces ouverts a l'arrivee : [{"workspace_id": ..., "role": ...}]
    acces: Mapped[list] = mapped_column(JSON, default=list)
    jeton: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    invitee_par: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expire_le: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acceptee_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    organization: Mapped["Organization"] = relationship()
