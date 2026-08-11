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
