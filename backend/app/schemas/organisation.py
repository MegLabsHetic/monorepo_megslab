"""Contrat de sortie des routes d'organisation."""

from pydantic import BaseModel


class OrganisationReponse(BaseModel):
    id: str
    nom: str
    # Nul si l'URL publique d'Airbyte n'est pas configuree.
    lien_airbyte: str | None = None
