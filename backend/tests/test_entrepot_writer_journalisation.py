"""Ce que l'ecrivain d'entrepot ecrit dans les journaux quand il echoue.

Sans marqueur `integration` : l'echec provoque ici est justement l'incapacite a
joindre l'entrepot, donc aucun service reel n'est necessaire. Le message que
DuckDB produit alors cite le DSN complet, mot de passe compris — c'est ce que
ces tests empechent de ressortir.
"""

import logging
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.entrepot_writer import EntrepotWriter, ErreurImport

MOT_DE_PASSE = "motdepasse-qui-ne-doit-jamais-etre-journalise"


@pytest.fixture
def entrepot_injoignable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un entrepot dont l'adresse ne repond pas : l'attache echoue en citant le DSN."""
    reglages = Settings(
        warehouse_lecture_host="127.0.0.1",
        warehouse_lecture_port=1,
        warehouse_postgres_database="warehouse",
        warehouse_postgres_username="megslab",
        warehouse_postgres_password=MOT_DE_PASSE,
    )
    monkeypatch.setattr("app.core.entrepot_writer.get_settings", lambda: reglages)


@pytest.fixture
def fichier_csv(tmp_path: Path) -> Path:
    chemin = tmp_path / "depot.csv"
    chemin.write_text("a,b\n1,2\n", encoding="utf-8")
    return chemin


def test_l_import_qui_echoue_ne_journalise_pas_le_mot_de_passe_de_l_entrepot(
    entrepot_injoignable: None, fichier_csv: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ErreurImport):
            EntrepotWriter("ws_test").importer(fichier_csv, "t")

    assert MOT_DE_PASSE not in caplog.text
    assert "password=***" in caplog.text


def test_la_suppression_qui_echoue_ne_journalise_pas_le_mot_de_passe(
    entrepot_injoignable: None, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ErreurImport):
            EntrepotWriter("ws_test").supprimer_tables(["une_table"])

    assert MOT_DE_PASSE not in caplog.text


def test_la_copie_qui_echoue_ne_journalise_pas_le_mot_de_passe(
    entrepot_injoignable: None, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(ErreurImport):
            EntrepotWriter("ws_test").copier_tables("demo", ["une_table"], "demo_")

    assert MOT_DE_PASSE not in caplog.text


def test_le_message_rendu_a_l_utilisateur_ne_contient_aucun_detail_technique(
    entrepot_injoignable: None, fichier_csv: Path
) -> None:
    with pytest.raises(ErreurImport) as echec:
        EntrepotWriter("ws_test").importer(fichier_csv, "t")

    assert MOT_DE_PASSE not in echec.value.raison
    assert "127.0.0.1" not in echec.value.raison
