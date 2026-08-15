"""Une source de donnees connectee par une organisation (ex. une base PostgreSQL).

Ne stocke jamais les identifiants de connexion (host/mot de passe) : Airbyte
les detient deja, chiffres, cote workspace de l'organisation. Dupliquer ce
secret ici n'apporterait rien et serait une surface de fuite en plus.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import HorodatageMixin

if TYPE_CHECKING:
    from app.models.organization import Organization


class StatutSource(str, enum.Enum):
    CONNECTEE = "connectee"  # source+destination crees cote Airbyte, pas encore synchronisee
    SYNCHRONISATION = "synchronisation"
    PRETE = "prete"
    ERREUR = "erreur"


class DataSource(HorodatageMixin, Base):
    __tablename__ = "data_sources"

    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    nom: Mapped[str] = mapped_column(String(255))
    type_source: Mapped[str] = mapped_column(String(50), default="postgres")
    statut: Mapped[StatutSource] = mapped_column(
        Enum(StatutSource, native_enum=False, length=20), default=StatutSource.CONNECTEE
    )

    airbyte_source_id: Mapped[str] = mapped_column(String(64))
    airbyte_connection_id: Mapped[str | None] = mapped_column(String(64), default=None)
    schema_entrepot: Mapped[str] = mapped_column(String(64))

    # Toutes les sources d'une organisation ecrivent dans le meme schema (pour
    # que l'analyse puisse joindre leurs tables). Ce prefixe evite que deux
    # sources ayant une table du meme nom s'ecrasent. Vide pour les sources
    # creees avant son introduction : leurs tables restent sans prefixe.
    prefixe_entrepot: Mapped[str] = mapped_column(String(32), default="")

    # Le schema decouvert, garde tel quel : sans ca, les tables d'une source ne
    # seraient consultables qu'une seule fois, juste apres sa connexion.
    # Forme : [{"nom": ..., "namespace": ..., "colonnes": [...]}]
    flux_decouverts: Mapped[list] = mapped_column(JSON, default=list)
    # Les flux que l'utilisateur a choisi de synchroniser, parmi les decouverts.
    flux_selectionnes: Mapped[list] = mapped_column(JSON, default=list)

    organization: Mapped["Organization"] = relationship()

    def table_entrepot(self, nom_flux: str) -> str:
        """Le nom que porte ce flux une fois copie dans l'entrepot."""
        return f"{self.prefixe_entrepot}{nom_flux}"

    @property
    def nb_tables(self) -> int:
        return len(self.flux_decouverts or [])

    @property
    def nb_colonnes(self) -> int:
        return sum(len(flux.get("colonnes", [])) for flux in self.flux_decouverts or [])
