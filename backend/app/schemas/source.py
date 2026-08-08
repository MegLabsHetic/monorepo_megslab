"""Contrats d'entree/sortie des routes de connexion de sources."""

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
    id: str
    nom: str
    statut: str
    flux_disponibles: list[FluxReponse] = []

    model_config = {"from_attributes": True}


class SynchronisationDemande(BaseModel):
    flux: list[str] = Field(min_length=1)


class SynchronisationReponse(BaseModel):
    job_id: int


class StatutSyncReponse(BaseModel):
    statut: str
    lignes_synchronisees: int | None = None
