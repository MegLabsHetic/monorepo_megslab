"""Contrats de la console plateforme, reservee a l'operateur."""

from datetime import datetime

from pydantic import BaseModel


class OrganisationPlateformeReponse(BaseModel):
    id: str
    nom: str
    cree_le: datetime
    nb_membres: int
    nb_espaces: int
    nb_sources: int
    nb_questions: int
    cout_dollars: float


class ComposantSanteReponse(BaseModel):
    nom: str
    # "ok", "ko" ou "non_teste" quand rien ne permet encore de l'eprouver.
    etat: str
    detail: str
    latence_ms: int | None = None


class SanteReponse(BaseModel):
    composants: list[ComposantSanteReponse]
    nb_organisations: int
    nb_utilisateurs: int
    cout_total_dollars: float
