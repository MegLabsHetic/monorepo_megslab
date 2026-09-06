"""Contrats des routes de tableaux de bord."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.question import AnalyseReponse, GraphiqueReponse, ResultatReponse


class DashboardReponse(BaseModel):
    id: str
    nom: str
    nb_widgets: int
    auteur: str
    auteur_id: str
    cree_le: datetime
    maj_le: datetime


class DashboardCreation(BaseModel):
    nom: str = Field(min_length=1, max_length=120)


class DashboardModification(BaseModel):
    nom: str = Field(min_length=1, max_length=120)


class EpinglageDemande(BaseModel):
    question_id: str
    titre: str | None = Field(default=None, max_length=120)


class WidgetModification(BaseModel):
    titre: str | None = Field(default=None, min_length=1, max_length=120)
    position: int | None = Field(default=None, ge=0)


class WidgetReponse(BaseModel):
    id: str
    titre: str
    sql: str
    question_id: str | None
    conversation_id: str | None
    position: int
    graphique: GraphiqueReponse | None
    # Le resultat tel que la requete vient de le rendre ; nul si elle a echoue.
    resultat: ResultatReponse | None
    analyse: AnalyseReponse | None
    erreur: str | None


class DashboardDetailReponse(BaseModel):
    id: str
    nom: str
    auteur: str
    auteur_id: str
    cree_le: datetime
    maj_le: datetime
    widgets: list[WidgetReponse]
    # Le moment ou les requetes ont ete rejouees : ce que montre le tableau est vrai a cet instant.
    rejoue_le: datetime
