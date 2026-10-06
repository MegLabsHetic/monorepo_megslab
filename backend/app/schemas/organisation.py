"""Contrats des routes d'organisation."""

from pydantic import BaseModel, Field


class OrganisationReponse(BaseModel):
    id: str
    nom: str
    # Le role de l'utilisateur courant : owner, admin ou member.
    role: str
    nb_espaces: int
    nb_membres: int


class OrganisationModification(BaseModel):
    nom: str = Field(min_length=1, max_length=255)
