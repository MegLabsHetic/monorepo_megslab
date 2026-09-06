"""Des questions de depart proposees a partir du schema reel de l'espace.

Un appel au modele, a effort minimal, sur le meme contexte que l'Analyste :
les suggestions ne peuvent donc parler que de tables qui existent. Le
resultat est garde une demi-heure par espace, pour que l'ouverture de la
page ne coute rien la plupart du temps.
"""

import time

from pydantic import BaseModel, Field

from app.agents.data import ContexteDonnees
from app.core.llm_client import Consommation, LLMClient

INSTRUCTIONS = """Tu proposes trois questions qu'un analyste metier poserait en francais sur
les donnees decrites, pour commencer a les explorer.

Regles :
- Chaque question doit pouvoir etre repondue avec une seule requete SQL sur les
  tables et colonnes listees. N'invente ni table ni colonne.
- Varie les angles : un comptage ou un classement, une evolution dans le temps
  si une colonne de date existe, une repartition par categorie si une colonne a
  des modalites.
- Une phrase courte par question, sans preambule, formulee comme on la dirait a
  l'oral. Pas de SQL, pas de nom de table brut."""

DUREE_CACHE_SECONDES = 30 * 60
NB_SUGGESTIONS = 3

_CACHE: dict[str, tuple[float, list[str]]] = {}


class Suggestions(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=5)


class SuggestionService:
    def __init__(self, llm: LLMClient | None = None, horloge=time.monotonic) -> None:
        self._llm = llm or LLMClient()
        self._horloge = horloge

    async def proposer(
        self, schema_entrepot: str, contexte: ContexteDonnees
    ) -> tuple[list[str], Consommation | None]:
        """Trois questions pour cet espace, depuis le cache si possible."""
        en_cache = _CACHE.get(schema_entrepot)
        if en_cache and self._horloge() - en_cache[0] < DUREE_CACHE_SECONDES:
            return list(en_cache[1]), None

        reponse = await self._llm.repondre(
            instructions=INSTRUCTIONS,
            question=f"Donnees disponibles :\n{contexte.texte()}",
            format_sortie=Suggestions,
            effort="low",
        )
        questions = [q.strip() for q in reponse.contenu.questions if q.strip()][:NB_SUGGESTIONS]
        _CACHE[schema_entrepot] = (self._horloge(), questions)
        return questions, reponse.consommation

    @staticmethod
    def oublier(schema_entrepot: str) -> None:
        _CACHE.pop(schema_entrepot, None)

    @staticmethod
    def oublier_tout() -> None:
        _CACHE.clear()
