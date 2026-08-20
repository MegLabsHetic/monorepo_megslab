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


class ResultatReponse(BaseModel):
    colonnes: list[str]
    lignes: list[list]
    tronque: bool


class QuestionReponse(BaseModel):
    id: str
    texte: str
    reponse: str
    sql: str | None
    resultat: ResultatReponse | None
    etapes: list[EtapeReponse]
    cout_dollars: float
    jetons: int
    duree_ms: int
    cree_le: datetime


class ContexteReponse(BaseModel):
    """Ce que le modele a reellement recu : le schema, et rien d'autre.

    Sert a l'interface pour montrer, sans le simuler, ce qui est parti au modele.
    """

    schema: str
    instructions: str
