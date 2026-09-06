"""Contrats des routes FinOps : budget et rapport de couts."""

from pydantic import BaseModel, Field


class BudgetReponse(BaseModel):
    budget_dollars: float | None
    depense_mois_dollars: float
    pourcentage: float | None
    seuil_alerte_pct: int
    bloquant: bool
    alerte: bool
    bloque: bool
    jours_ecoules: float
    jours_dans_le_mois: int
    # Un simple prorata de la depense sur les jours ecoules : un ordre de grandeur.
    prevision_fin_de_mois_dollars: float


class BudgetDemande(BaseModel):
    # Nul pour retirer le budget.
    budget_dollars: float | None = Field(default=None, ge=0)
    seuil_alerte_pct: int = Field(default=80, ge=1, le=100)
    bloquant: bool = True


class LigneReponse(BaseModel):
    cle: str
    libelle: str
    cout_dollars: float
    nb_questions: int
    jetons: int = 0


class JetonsReponse(BaseModel):
    entree: int
    sortie: int
    cache_lus: int
    cache_ecrits: int
    taux_cache: float | None


class RapportReponse(BaseModel):
    annee: int
    mois: int
    total_dollars: float
    nb_questions: int
    duree_moyenne_ms: int
    jetons: JetonsReponse
    par_jour: list[LigneReponse]
    par_utilisateur: list[LigneReponse]
    par_espace: list[LigneReponse]
    par_agent: list[LigneReponse]
    # Present seulement pour le mois en cours.
    budget: BudgetReponse | None


class PoidsEspaceReponse(BaseModel):
    espace_id: str
    espace_nom: str
    nb_tables: int
    octets: int
