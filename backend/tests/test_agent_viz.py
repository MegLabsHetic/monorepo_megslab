"""L'agent Viz tranche seul les cas evidents, et verifie ce que le modele propose."""

from app.agents.viz import LIGNES_MAX_GRAPHIQUE, AgentViz, SpecGraphique
from app.core.duckdb_engine import Resultat
from app.core.llm_client import Consommation, Reponse

CONSOMMATION = Consommation(
    jetons_entree=10, jetons_sortie=5, jetons_cache_lus=0, jetons_cache_ecrits=0
)


class FauxLLM:
    def __init__(self, spec: SpecGraphique) -> None:
        self.spec = spec
        self.appels = 0

    async def repondre(self, *, instructions, question, format_sortie, effort):
        self.appels += 1
        return Reponse(contenu=self.spec, consommation=CONSOMMATION)


def _resultat(n: int = 5) -> Resultat:
    return Resultat(
        colonnes=["etat", "commandes", "delai"],
        lignes=[(f"E{i}", 10 * i, 1.5 * i) for i in range(n)],
        tronque=False,
    )


def test_les_cas_sans_graphique_sont_tranches_sans_appeler_le_modele() -> None:
    agent = AgentViz(FauxLLM(SpecGraphique(type="barres")))  # type: ignore[arg-type]

    une_ligne = Resultat(colonnes=["n"], lignes=[(3,)], tronque=False)
    assert agent.motif_de_refus(une_ligne) == "une seule ligne"
    assert agent.motif_de_refus(_resultat(LIGNES_MAX_GRAPHIQUE + 1)) is not None
    que_du_texte = Resultat(colonnes=["a", "b"], lignes=[("x", "y"), ("z", "w")], tronque=False)
    assert agent.motif_de_refus(que_du_texte) == "aucune colonne numerique"
    assert agent.motif_de_refus(_resultat()) is None


async def test_une_proposition_coherente_est_acceptee() -> None:
    llm = FauxLLM(
        SpecGraphique(type="barres", axe_x="etat", axes_y=["commandes"], titre="Commandes par etat")
    )

    reponse = await AgentViz(llm).choisir("Combien de commandes par etat ?", _resultat())  # type: ignore[arg-type]

    assert reponse.contenu.type == "barres"
    assert reponse.contenu.axes_y == ["commandes"]
    assert reponse.contenu.titre == "Commandes par etat"
    assert reponse.consommation == CONSOMMATION


async def test_un_axe_inexistant_annule_le_graphique() -> None:
    llm = FauxLLM(SpecGraphique(type="lignes", axe_x="mois", axes_y=["commandes"]))

    reponse = await AgentViz(llm).choisir("Evolution ?", _resultat())  # type: ignore[arg-type]

    assert reponse.contenu.type == "aucun"
    assert "incoherente" in reponse.contenu.raison


async def test_les_axes_y_non_numeriques_sont_ecartes_et_le_titre_complete() -> None:
    llm = FauxLLM(SpecGraphique(type="barres", axe_x="etat", axes_y=["etat", "delai", "commandes"]))

    reponse = await AgentViz(llm).choisir("Detail ?", _resultat())  # type: ignore[arg-type]

    assert reponse.contenu.axes_y == ["delai", "commandes"]
    assert reponse.contenu.titre == "delai, commandes par etat"
