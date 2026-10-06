"""Contrats du partage public d'un tableau de bord.

Ces schemas reprennent ceux des tableaux, amputes de tout ce qui designe
l'interieur du client : ni identifiant d'espace, ni organisation, ni auteur,
ni lien vers la conversation d'origine. Un visiteur sans compte voit des
chiffres et le SQL qui les produit, rien de la structure qui les heberge.
"""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.dashboard import AnalyseReponse, GraphiqueReponse, ResultatReponse


class WidgetPartageReponse(BaseModel):
    titre: str
    # Le SQL reste visible : c'est la promesse du produit, et elle vaut aussi
    # pour celui qui recoit le lien sans avoir de compte.
    sql: str
    position: int
    graphique: GraphiqueReponse | None
    resultat: ResultatReponse | None
    analyse: AnalyseReponse | None
    erreur: str | None


class TableauPartageReponse(BaseModel):
    nom: str
    widgets: list[WidgetPartageReponse]
    # Le moment du rejeu : ce que montre la page est vrai a cet instant, pas
    # au moment ou le lien a ete cree.
    rejoue_le: datetime


class PartageReponse(BaseModel):
    """Le jeton seul : c'est au client de construire l'URL publique."""

    jeton: str
