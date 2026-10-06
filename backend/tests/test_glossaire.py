"""Le glossaire metier enrichit le contexte, et reste sans effet quand il est vide."""

from app.agents.data import AgentData
from app.core.duckdb_engine import ColonneProfil, TableProfil


class MoteurProfil:
    schema_entrepot = "org_test"

    def profil_complet(self) -> list[TableProfil]:
        return [
            TableProfil(
                nom="o_head",
                nb_lignes=99_441,
                colonnes=(
                    ColonneProfil("o_id", "VARCHAR", 0.0, 99_441, None),
                    ColonneProfil(
                        "o_status", "VARCHAR", 0.0, 3, ("canceled", "delivered", "shipped")
                    ),
                ),
            )
        ]


def _contexte():
    return AgentData(MoteurProfil()).decrire()


def test_sans_glossaire_le_texte_est_exactement_celui_d_avant() -> None:
    """Un espace qui n'a rien annote ne doit voir aucun changement de comportement."""
    contexte = _contexte()
    assert contexte.texte() == contexte.texte({})
    assert contexte.texte() == contexte.texte(None)


def test_une_definition_de_colonne_rejoint_la_description() -> None:
    contexte = _contexte()
    texte = contexte.texte({("o_head", "o_status"): "statut de la commande"})
    assert "o_status VARCHAR - statut de la commande" in texte


def test_la_definition_precede_les_modalites() -> None:
    """Le modele lit ce qui vient en tete : la levee d'ambiguite passe devant."""
    contexte = _contexte()
    ligne = [
        li
        for li in contexte.texte({("o_head", "o_status"): "statut"}).splitlines()
        if "o_status" in li
    ][0]
    assert ligne.index("statut") < ligne.index("modalites")


def test_une_definition_de_table_rejoint_son_entete() -> None:
    contexte = _contexte()
    texte = contexte.texte({("o_head", ""): "en-tete de commande, une ligne par commande"})
    assert 'entrepot."o_head" (99 441 lignes) - en-tete de commande' in texte


def test_une_definition_qui_vise_une_colonne_absente_est_ignoree() -> None:
    """Une annotation devenue obsolete ne doit pas polluer le contexte."""
    contexte = _contexte()
    assert contexte.texte({("o_head", "colonne_supprimee"): "ancienne"}) == contexte.texte()


def test_une_definition_qui_vise_une_table_absente_est_ignoree() -> None:
    contexte = _contexte()
    assert contexte.texte({("table_disparue", "x"): "ancienne"}) == contexte.texte()
