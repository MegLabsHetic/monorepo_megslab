"""Contrats des routes du glossaire metier."""

from pydantic import BaseModel, Field

from app.models.annotation import DESCRIPTION_MAX, NOM_MAX


class AnnotationDemande(BaseModel):
    table_nom: str = Field(min_length=1, max_length=NOM_MAX)
    # Vide : la definition porte sur la table elle-meme.
    colonne_nom: str = Field(default="", max_length=NOM_MAX)
    description: str = Field(min_length=1, max_length=DESCRIPTION_MAX)


class AnnotationReponse(BaseModel):
    id: str
    table_nom: str
    colonne_nom: str
    description: str
    porte_sur_la_table: bool


class GlossaireReponse(BaseModel):
    total: int
    annotations: list[AnnotationReponse]
