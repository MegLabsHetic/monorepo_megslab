"""L'ecriture dans l'entrepot, contre le vrai entrepot.

Ces tests portent le marqueur `integration` et sont exclus de la CI. Ils
existent parce qu'une doublure ne peut pas repondre a la seule question qui
compte ici : ce SQL passe-t-il vraiment sur cette version de DuckDB et de son
extension Postgres ? Une copie qui semblait fonctionner en test unitaire
echouait en reel sur une fonction inexistante.
"""

import pytest

from app.core.duckdb_engine import PREFIXE_TECHNIQUE, DuckDBEngine
from app.core.entrepot_writer import EntrepotWriter

SCHEMA_DEMO = "demo_olist"
SCHEMA_JETABLE = "ws_test_entrepot_writer"
TABLES = ["sellers", "product_category_name_translation"]

pytestmark = pytest.mark.integration


@pytest.fixture
def writer() -> EntrepotWriter:
    ecrivain = EntrepotWriter(SCHEMA_JETABLE)
    yield ecrivain
    ecrivain.supprimer_tables([f"demo_{table}" for table in TABLES])


def test_copier_rend_les_colonnes_metier_et_les_lignes_arrivent(writer: EntrepotWriter) -> None:
    colonnes = writer.copier_tables(SCHEMA_DEMO, TABLES, "demo_")

    assert set(colonnes) == set(TABLES)
    for noms in colonnes.values():
        assert noms, "une table copiee sans colonne"
        assert not any(nom.startswith(PREFIXE_TECHNIQUE) for nom in noms)

    # La copie est faite par Postgres : les lignes doivent etre la, relues par
    # une connexion neuve qui ne partage rien avec celle qui a ecrit.
    moteur = DuckDBEngine(SCHEMA_JETABLE)
    assert set(moteur.lister_tables()) >= {f"demo_{table}" for table in TABLES}
    assert moteur.executer('SELECT count(*) AS n FROM entrepot."demo_sellers"').lignes[0][0] > 0


def test_copier_deux_fois_remplace_sans_echouer(writer: EntrepotWriter) -> None:
    writer.copier_tables(SCHEMA_DEMO, TABLES[:1], "demo_")
    writer.copier_tables(SCHEMA_DEMO, TABLES, "demo_")

    moteur = DuckDBEngine(SCHEMA_JETABLE)
    assert moteur.executer('SELECT count(*) AS n FROM entrepot."demo_sellers"').lignes[0][0] > 0


def test_supprimer_fait_tomber_les_tables(writer: EntrepotWriter) -> None:
    writer.copier_tables(SCHEMA_DEMO, TABLES, "demo_")

    writer.supprimer_tables([f"demo_{table}" for table in TABLES])

    restantes = DuckDBEngine(SCHEMA_JETABLE).lister_tables()
    assert all(f"demo_{table}" not in restantes for table in TABLES)
