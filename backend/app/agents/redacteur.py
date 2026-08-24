"""L'agent Redacteur : ecrit en francais ce que l'Analyste a calcule.

Il ne calcule rien. Il recoit un resultat deja obtenu et le formule. C'est ce
qui garantit qu'aucun chiffre de la reponse ne vient de son imagination : ils
sont tous dans les lignes qu'on lui donne, et il a l'ordre de ne pas en inventer.
"""

from pydantic import BaseModel, Field

from app.core.duckdb_engine import Resultat
from app.core.llm_client import LLMClient, Reponse

INSTRUCTIONS = """Tu rediges, en francais, la reponse a une question posee sur des donnees.

On te donne la question, la requete SQL qui a servi, et son resultat. Tu n'as
aucun autre acces aux donnees.

Regles :
- Reponds directement, en deux a cinq phrases. Pas de titre, pas de liste a puces.
- N'utilise que les chiffres presents dans le resultat. N'en invente et n'en extrapole aucun.
- Cite les chiffres importants avec leur unite ou leur contexte (commandes, euros, %).
- Si le resultat est vide, dis-le simplement.
- Tu ne vois parfois que les premieres lignes d'un resultat plus long : appuie-toi sur
  elles et sur l'analyse statistique, sans dire que des lignes manquent — l'utilisateur,
  lui, voit tout le tableau.
- Ne mentionne pas le SQL ni le fait qu'une requete a ete executee : parle des donnees.
- Si une analyse statistique est fournie, reprends-en l'essentiel en une phrase, en
  disant qu'il s'agit d'une projection lineaire. N'ajoute aucune analyse de ton cru."""

# Ce qui part au modele est borne : quelques lignes, des cellules coupees. Le
# Redacteur formule une reponse, il n'a pas besoin de la table entiere.
LIGNES_MAX_ENVOYEES = 20
LONGUEUR_CELLULE_MAX = 80


class Redaction(BaseModel):
    reponse: str = Field(description="La reponse en francais, deux a cinq phrases")


class Redacteur:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    async def rediger(
        self, question: str, sql: str, resultat: Resultat, analyse: str | None = None
    ) -> Reponse[Redaction]:
        return await self._llm.repondre(
            instructions=INSTRUCTIONS,
            question=_composer(question, sql, resultat, analyse),
            format_sortie=Redaction,
            # Formuler n'est pas raisonner : l'effort minimal suffit, et coute
            # moins cher.
            effort="low",
        )


def _composer(question: str, sql: str, resultat: Resultat, analyse: str | None) -> str:
    lignes = resultat.lignes[:LIGNES_MAX_ENVOYEES]
    tableau = "\n".join(" | ".join(_cellule(valeur) for valeur in ligne) for ligne in lignes)
    entete = " | ".join(resultat.colonnes)
    precision = ""
    if len(resultat.lignes) > LIGNES_MAX_ENVOYEES:
        precision = f"\n(Tu vois les {len(lignes)} premieres lignes sur {len(resultat.lignes)}.)"
    if resultat.tronque:
        precision += "\n(La requete elle-meme a ete plafonnee : il existe d'autres lignes.)"

    complement = (
        f"\n\nAnalyse statistique (calculee, a citer telle quelle) :\n{analyse}" if analyse else ""
    )
    return (
        f"Question : {question}\n\n"
        f"Requete executee :\n{sql}\n\n"
        f"Resultat ({len(resultat.lignes)} ligne(s)) :\n{entete}\n{tableau}{precision}"
        f"{complement}"
    )


def _cellule(valeur: object) -> str:
    texte = "vide" if valeur is None else str(valeur)
    return texte if len(texte) <= LONGUEUR_CELLULE_MAX else texte[:LONGUEUR_CELLULE_MAX] + "…"
