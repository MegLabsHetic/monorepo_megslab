"""Le moteur lit l'entrepot, coupe les gros resultats, et reste verrouille.

Ces tests parlent au vrai entrepot : ils portent le marqueur `integration` et
sont exclus de la CI (`pytest -m "not integration"`). Ils supposent le tunnel
de lecture ouvert (voir README).
"""

import duckdb
import pytest

from app.core.duckdb_engine import LIGNES_MAX, DuckDBEngine, ErreurRequete

SCHEMA_DEMO = "org_143f78fef7fc4a528e6c9b1aad48eeac"

pytestmark = pytest.mark.integration


@pytest.fixture
def moteur() -> DuckDBEngine:
    return DuckDBEngine(SCHEMA_DEMO)


def test_lit_les_donnees_de_l_entrepot(moteur: DuckDBEngine) -> None:
    resultat = moteur.executer("SELECT count(*) AS n FROM entrepot.orders")

    assert resultat.colonnes == ["n"]
    assert resultat.lignes[0][0] > 0
    assert resultat.tronque is False


def test_ne_voit_que_les_tables_de_son_organisation(moteur: DuckDBEngine) -> None:
    tables = moteur.lister_tables()

    assert "orders" in tables
    assert all("." not in table for table in tables)


def test_un_resultat_trop_gros_est_coupe_et_signale(moteur: DuckDBEngine) -> None:
    resultat = moteur.executer("SELECT order_id FROM entrepot.orders", lignes_max=10)

    assert resultat.nb_lignes == 10
    assert resultat.tronque is True


def test_l_acces_fichier_reste_bloque_par_le_moteur(moteur: DuckDBEngine) -> None:
    """Deuxieme barriere : meme un SQL qui aurait echappe au garde-fou ne lit
    pas le disque, parce que le moteur lui-meme le refuse."""
    with pytest.raises(ErreurRequete):
        moteur.executer("SELECT * FROM read_csv_auto('C:/Windows/win.ini')")


def test_l_ecriture_reste_bloquee_par_le_moteur(moteur: DuckDBEngine) -> None:
    with pytest.raises(ErreurRequete):
        moteur.executer("DELETE FROM entrepot.orders")


def test_une_table_inexistante_donne_un_message_utile(moteur: DuckDBEngine) -> None:
    with pytest.raises(ErreurRequete) as refus:
        moteur.executer("SELECT * FROM entrepot.table_qui_nexiste_pas")

    assert "n'existe pas" in refus.value.raison


def test_la_configuration_ne_peut_pas_etre_deverrouillee() -> None:
    """Le verrou de configuration tient : on ne peut pas rouvrir l'acces externe."""
    moteur = DuckDBEngine(SCHEMA_DEMO)
    connexion = moteur._connexion_verrouillee()
    try:
        with pytest.raises(duckdb.Error):
            connexion.execute("SET enable_external_access=true")
    finally:
        connexion.close()


def test_la_limite_par_defaut_est_appliquee(moteur: DuckDBEngine) -> None:
    resultat = moteur.executer("SELECT order_id FROM entrepot.orders")

    assert resultat.nb_lignes == LIGNES_MAX
    assert resultat.tronque is True
