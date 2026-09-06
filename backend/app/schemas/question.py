"""Contrats d'entree/sortie de l'assistant."""

from datetime import datetime

from pydantic import BaseModel, Field


class QuestionDemande(BaseModel):
    texte: str = Field(min_length=3, max_length=2000)


class EtapeReponse(BaseModel):
    agent: str
    statut: str
    duree_ms: int
    detail: str = ""
    cout_dollars: float = 0.0
    jetons: int = 0


class ResultatReponse(BaseModel):
    colonnes: list[str]
    lignes: list[list]
    tronque: bool


class AnomalieReponse(BaseModel):
    x: str
    y: float
    ecart: float


class PrevisionReponse(BaseModel):
    x: str
    y: float
    y_min: float
    y_max: float


class AnalyseReponse(BaseModel):
    """Ce que l'agent ML a calcule : une droite, ses ecarts, sa projection."""

    colonne_x: str
    colonne_y: str
    nb_points: int
    pente: float
    variation_pct: float | None
    r2: float
    tendance: str
    anomalies: list[AnomalieReponse]
    previsions: list[PrevisionReponse]


class GraphiqueReponse(BaseModel):
    type: str
    axe_x: str
    axes_y: list[str]
    titre: str
    raison: str = ""


class QuestionReponse(BaseModel):
    id: str
    conversation_id: str
    texte: str
    reponse: str
    sql: str | None
    resultat: ResultatReponse | None
    analyse: AnalyseReponse | None = None
    graphique: GraphiqueReponse | None = None
    etapes: list[EtapeReponse]
    cout_dollars: float
    jetons: int
    duree_ms: int
    cree_le: datetime


class ContexteReponse(BaseModel):
    """Ce que le modele a reellement recu : le contexte de l'entrepot, et rien d'autre.

    Sert a l'interface pour montrer, sans le simuler, ce qui est parti au modele.
    """

    schema: str
    instructions: str
    nb_tables: int
    nb_colonnes: int
    nb_lignes: int
