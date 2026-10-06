"""Contrats des routes d'espaces de travail."""

from datetime import datetime

from pydantic import BaseModel, Field


class EspaceReponse(BaseModel):
    id: str
    nom: str
    # Le role de l'utilisateur courant dans cet espace : admin, member ou viewer.
    role: str
    schema_entrepot: str
    # Nul si l'URL publique d'Airbyte n'est pas configuree.
    lien_airbyte: str | None = None
    cree_le: datetime


class EspaceCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=120)


class EspaceModification(BaseModel):
    nom: str = Field(min_length=1, max_length=120)


class AccesEspaceReponse(BaseModel):
    user_id: str
    email: str
    nom_complet: str
    role: str


class AccesEspaceDemande(BaseModel):
    # Nul pour retirer l'acces.
    role: str | None = None
