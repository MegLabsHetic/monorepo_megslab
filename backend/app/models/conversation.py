"""Un fil de questions dans un espace de travail.

Une conversation appartient a l'espace, pas a son auteur : les analyses sont
un savoir d'equipe, chaque membre de l'espace peut les relire. Les questions
de suivi voient les echanges precedents du meme fil.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace

TITRE_MAX = 120


class Conversation(HorodatageMixin, Base):
    __tablename__ = "conversations"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    titre: Mapped[str] = mapped_column(String(TITRE_MAX), default="Nouvelle conversation")
    epinglee: Mapped[bool] = mapped_column(Boolean, default=False)

    workspace: Mapped["Workspace"] = relationship()
    user: Mapped["User"] = relationship()
