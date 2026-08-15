"""Contrats d'entree/sortie des routes de connexion de sources."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConnexionPostgresDemande(BaseModel):
    nom: str = Field(min_length=1)
    host: str = Field(min_length=1)
    port: int = 5432
    database: str = Field(min_length=1)
    username: str = Field(min_length=1)
    mot_de_passe: str


class FluxReponse(BaseModel):
    nom: str
    namespace: str
    colonnes: list[str]


class SourceReponse(BaseModel):
    """Vue complete d'une source : ce que le catalogue et la fiche detail affichent."""

    id: str
    nom: str
    type_source: str
    statut: str
    schema_entrepot: str
    nb_tables: int
    nb_colonnes: int
    flux_disponibles: list[FluxReponse]
    flux_selectionnes: list[str]
    cree_le: datetime


class SynchronisationDemande(BaseModel):
    flux: list[str] = Field(min_length=1)


class SynchronisationReponse(BaseModel):
    job_id: int


class StatutSyncReponse(BaseModel):
    statut: str
    lignes_synchronisees: int | None = None


class TableReponse(BaseModel):
    nom: str
    nb_lignes: int


class ApercuReponse(BaseModel):
    colonnes: list[str]
    lignes: list[list]
    tronque: bool


class ProfilColonneReponse(BaseModel):
    """Le profil d'une colonne, tel que le moteur l'a calcule.

    Les champs numeriques sont optionnels : ils n'ont pas de sens sur une
    colonne de texte, et on prefere ne rien afficher plutot qu'un zero invente.
    """

    colonne: str
    type: str
    nb_valeurs: int | None = None
    pourcentage_nuls: float | None = None
    # DuckDB compte les valeurs distinctes de facon approximative (HyperLogLog) :
    # sur une petite table l'estimation peut depasser le nombre de lignes. Le nom
    # dit l'approximation pour qu'aucune interface ne l'affiche comme un exact.
    valeurs_distinctes_approx: int | None = None
    minimum: str | None = None
    maximum: str | None = None
    moyenne: str | None = None
