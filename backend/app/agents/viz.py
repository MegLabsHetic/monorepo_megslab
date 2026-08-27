"""L'agent Viz : decide si un resultat merite un graphique, et lequel.

Il ne dessine rien : il rend une specification (type, axes, titre) que
l'interface trace elle-meme. Il ne voit qu'un echantillon du resultat, et sa
proposition est verifiee contre les vraies colonnes avant d'etre acceptee —
un axe qui n'existe pas, et on se passe de graphique.

Les cas ou un graphique n'a pas de sens (une seule ligne, aucune colonne
numerique, trop de lignes) sont tranches ici sans appeler le modele.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.agents.valeurs import genre_colonne
from app.core.duckdb_engine import Resultat
from app.core.llm_client import LLMClient, Reponse

INSTRUCTIONS = """Tu choisis comment representer graphiquement le resultat d'une requete,
ou tu decides qu'aucun graphique ne convient.

On te donne la question, les colonnes avec leur genre (nombre, date, texte),
et quelques lignes. Tu rends :
- `type` : "barres" pour comparer des categories, "lignes" pour une evolution
  dans le temps (axe x de genre date ou annee), "aucun" si rien n'apporte de
  lecture utile (une seule valeur, un tableau de detail, des identifiants).
- `axe_x` : le nom exact d'une colonne, categorie ou date.
- `axes_y` : un a trois noms exacts de colonnes numeriques a tracer.
- `titre` : court, en francais, sans point final.
- `raison` : une phrase sur ton choix.

N'invente aucun nom de colonne. Si tu hesites, prefere "aucun"."""

LIGNES_MAX_GRAPHIQUE = 60
LIGNES_ECHANTILLON = 6
AXES_Y_MAX = 3


class SpecGraphique(BaseModel):
    type: Literal["barres", "lignes", "aucun"]
    axe_x: str = ""
    axes_y: list[str] = Field(default_factory=list)
    titre: str = ""
    raison: str = ""


class AgentViz:
    def __init__(self, llm: LLMClient | None = None) -> None:
        self._llm = llm or LLMClient()

    def motif_de_refus(self, resultat: Resultat) -> str | None:
        """Pourquoi on ne dessinera pas — ou None si ca vaut la peine de demander."""
        if resultat.nb_lignes < 2:
            return "une seule ligne"
        if resultat.nb_lignes > LIGNES_MAX_GRAPHIQUE:
            return f"plus de {LIGNES_MAX_GRAPHIQUE} lignes"
        if "nombre" not in _genres(resultat).values():
            return "aucune colonne numerique"
        return None

    async def choisir(self, question: str, resultat: Resultat) -> Reponse[SpecGraphique]:
        reponse = await self._llm.repondre(
            instructions=INSTRUCTIONS,
            question=_composer(question, resultat),
            format_sortie=SpecGraphique,
            # Choisir un type de graphique ne demande pas de raisonner longtemps.
            effort="low",
        )
        return Reponse(
            contenu=_verifier(reponse.contenu, resultat), consommation=reponse.consommation
        )


def _genres(resultat: Resultat) -> dict[str, str]:
    colonnes = list(zip(*resultat.lignes)) if resultat.lignes else []
    return {nom: genre_colonne(list(valeurs)) for nom, valeurs in zip(resultat.colonnes, colonnes)}


def _composer(question: str, resultat: Resultat) -> str:
    genres = _genres(resultat)
    description = "\n".join(f"- {nom} ({genre})" for nom, genre in genres.items())
    echantillon = "\n".join(
        " | ".join("vide" if v is None else str(v) for v in ligne)
        for ligne in resultat.lignes[:LIGNES_ECHANTILLON]
    )
    return (
        f"Question : {question}\n\n"
        f"Colonnes ({resultat.nb_lignes} lignes au total) :\n{description}\n\n"
        f"Premieres lignes :\n{echantillon}"
    )


def _verifier(spec: SpecGraphique, resultat: Resultat) -> SpecGraphique:
    """La proposition du modele ne vaut que si elle nomme de vraies colonnes."""
    if spec.type == "aucun":
        return spec
    genres = _genres(resultat)
    axes_y = [axe for axe in spec.axes_y if genres.get(axe) == "nombre"][:AXES_Y_MAX]
    if spec.axe_x not in genres or spec.axe_x in axes_y or not axes_y:
        return SpecGraphique(type="aucun", raison="proposition incoherente avec les colonnes")
    return SpecGraphique(
        type=spec.type,
        axe_x=spec.axe_x,
        axes_y=axes_y,
        titre=spec.titre.strip() or f"{', '.join(axes_y)} par {spec.axe_x}",
        raison=spec.raison,
    )
