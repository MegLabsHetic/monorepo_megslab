"""Une question posee a l'assistant, avec ce qu'elle a produit et coute.

On garde le SQL execute et le cout : « chaque analyse affiche ce qu'elle coute »
est une promesse du produit, et elle ne tient que si c'est mesure et conserve.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.user import User
    from app.models.workspace import Workspace


class Question(HorodatageMixin, Base):
    __tablename__ = "questions"

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))

    texte: Mapped[str] = mapped_column(Text)
    reponse: Mapped[str] = mapped_column(Text)
    # Nul quand l'Analyste a juge la question sans reponse dans le schema.
    sql: Mapped[str | None] = mapped_column(Text, default=None)
    # Ce que l'Analyste dit calculer, en francais : la lecture humaine du SQL.
    explication: Mapped[str] = mapped_column(Text, default="", server_default="")
    # L'avis de l'utilisateur sur la reponse : 1 (utile), -1 (fausse ou inutile), nul sinon.
    avis: Mapped[int | None] = mapped_column(Integer, default=None)
    commentaire_avis: Mapped[str] = mapped_column(Text, default="", server_default="")
    nb_lignes: Mapped[int | None] = mapped_column(Integer, default=None)
    # Un extrait borne du resultat, pour relire une reponse sans re-executer.
    # Forme : {"colonnes": [...], "lignes": [[...]], "tronque": bool}
    resultat: Mapped[dict | None] = mapped_column(JSON, default=None)
    # Ce que l'agent ML a calcule sur le resultat (tendance, anomalies,
    # projection), et le graphique choisi par l'agent Viz. Nuls quand le
    # resultat ne s'y pretait pas.
    analyse: Mapped[dict | None] = mapped_column(JSON, default=None)
    graphique: Mapped[dict | None] = mapped_column(JSON, default=None)

    # Forme : [{"agent": ..., "statut": ..., "duree_ms": ..., "detail": ...}]
    etapes: Mapped[list] = mapped_column(JSON, default=list)
    cout_dollars: Mapped[float] = mapped_column(Float, default=0.0)
    jetons: Mapped[int] = mapped_column(Integer, default=0)
    # Les jetons par nature : c'est ce qui permet de voir la part du cache
    # de prompt, et donc ce que coute vraiment un schema envoye a chaque question.
    jetons_entree: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jetons_sortie: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jetons_cache_lus: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    jetons_cache_ecrits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    duree_ms: Mapped[int] = mapped_column(Integer, default=0)

    workspace: Mapped["Workspace"] = relationship()
    conversation: Mapped["Conversation"] = relationship()
    user: Mapped["User"] = relationship()
