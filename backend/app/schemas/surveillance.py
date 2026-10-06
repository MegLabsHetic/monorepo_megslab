"""Contrats des routes de surveillance."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.surveillance import TITRE_MAX, Declencheur


class SurveillanceDemande(BaseModel):
    titre: str = Field(min_length=1, max_length=TITRE_MAX)
    sql: str = Field(min_length=1)
    declencheur: Declencheur = Declencheur.ANOMALIE
    # Exige pour les declencheurs de seuil, ignore pour les autres.
    seuil: float | None = None
    heure: int = Field(default=8, ge=0, le=23)


class SurveillanceReponse(BaseModel):
    id: str
    titre: str
    sql: str
    declencheur: Declencheur
    seuil: float | None
    heure: int
    active: bool
    derniere_execution: datetime | None
    dernier_etat: str


class VerdictReponse(BaseModel):
    """Le resultat d'une execution declenchee a la main, pour essayer sans attendre."""

    notifier: bool
    message: str
    erreur: str | None
