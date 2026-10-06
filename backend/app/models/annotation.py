"""Ce que l'entreprise sait de ses colonnes, et que le schema ne dit pas.

Un nom de colonne herite d'Airbyte ne porte aucun sens metier : `o_status` ne
dit pas qu'il s'agit du statut d'une commande, ni quelles valeurs il prend. Le
modele doit alors deviner, et deux des trois ecarts mesures sur notre jeu
d'evaluation viennent exactement de la : pas d'une faute technique, mais d'une
definition absente.

Ces annotations sont ecrites par un administrateur et rejoignent le contexte
envoye a l'Analyste. Le glossaire est donc **emergent** : il se construit a
l'usage, a partir des corrections. Il n'est jamais un prealable - un espace
sans aucune annotation fonctionne exactement comme avant.
"""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.workspace import Workspace

NOM_MAX = 200
DESCRIPTION_MAX = 500


class AnnotationCatalogue(HorodatageMixin, Base):
    """Une description libre attachee a une table, ou a une de ses colonnes."""

    __tablename__ = "annotations_catalogue"
    __table_args__ = (
        # Une seule annotation par cible : la reecrire remplace l'ancienne.
        # Une colonne vide designe la table elle-meme.
        UniqueConstraint("workspace_id", "table_nom", "colonne_nom", name="uq_annotation_cible"),
    )

    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    table_nom: Mapped[str] = mapped_column(String(NOM_MAX))
    # Chaine vide plutot que NULL : les contraintes d'unicite ignorent les NULL
    # sur certains moteurs, ce qui autoriserait des doublons silencieux.
    colonne_nom: Mapped[str] = mapped_column(String(NOM_MAX), default="", server_default="")
    description: Mapped[str] = mapped_column(Text)

    workspace: Mapped["Workspace"] = relationship()
    user: Mapped["User"] = relationship()

    @property
    def porte_sur_la_table(self) -> bool:
        return not self.colonne_nom
