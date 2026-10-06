"""Le garde-fou SQL laisse passer les lectures et refuse tout le reste.

Les cas de refus sont ecrits comme des tentatives de contournement : c'est la
seule facon utile de tester une liste blanche.
"""

import pytest

from app.core.sql_guard import SqlRefuse, valider


@pytest.mark.parametrize(
    "sql",
    [
        "select 1",
        "SELECT order_status, count(*) FROM entrepot.orders GROUP BY 1",
        "with recents as (select * from entrepot.orders limit 10) select count(*) from recents",
        "select * from entrepot.orders where order_status = 'delivered' order by order_id limit 5",
        "select a.order_id from entrepot.orders a join entrepot.products b on true",
        "select count(*) from entrepot.orders union all select count(*) from entrepot.products",
        "select (select count(*) from entrepot.orders) as total",
    ],
)
def test_les_lectures_sont_acceptees(sql: str) -> None:
    assert valider(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "delete from entrepot.orders",
        "update entrepot.orders set order_status = 'x'",
        "insert into entrepot.orders values (1)",
        "drop table entrepot.orders",
        "create table nouvelle as select 1",
        "alter table entrepot.orders add column x int",
        "truncate table entrepot.orders",
        "attach 'ailleurs.db' as ailleurs",
        "detach entrepot",
        "copy entrepot.orders to 'sortie.csv'",
        "install httpfs",
        "load httpfs",
        "pragma database_list",
        "set enable_external_access=true",
    ],
)
def test_tout_ce_qui_n_est_pas_une_lecture_est_refuse(sql: str) -> None:
    with pytest.raises(SqlRefuse):
        valider(sql)


def test_une_ecriture_cachee_derriere_une_lecture_est_refusee() -> None:
    """`SELECT 1; DROP TABLE t` ne doit pas passer sur la foi de sa premiere moitie."""
    with pytest.raises(SqlRefuse):
        valider("select 1; drop table entrepot.orders")


def test_une_ecriture_dans_une_cte_est_refusee() -> None:
    with pytest.raises(SqlRefuse):
        valider("with x as (delete from entrepot.orders returning *) select * from x")


@pytest.mark.parametrize(
    "sql",
    [
        "select * from read_csv_auto('C:/Windows/win.ini')",
        "select * from read_parquet('https://exemple.fr/donnees.parquet')",
        "select * from glob('C:/*')",
        "select * from postgres_query('entrepot', 'select 1')",
    ],
)
def test_les_fonctions_qui_lisent_fichiers_ou_reseau_sont_refusees(sql: str) -> None:
    with pytest.raises(SqlRefuse):
        valider(sql)


def test_le_sql_est_regenere_depuis_l_arbre_valide() -> None:
    """Ce qui est execute vient de l'arbre compris par l'analyseur, pas du texte
    d'origine : un commentaire glisse dans la requete ne survit pas."""
    regenere = valider("select /* commentaire */ 1 as x")

    assert "commentaire" not in regenere
    assert "SELECT" in regenere.upper()


def test_une_requete_illisible_est_refusee() -> None:
    with pytest.raises(SqlRefuse):
        valider("ceci n'est pas du sql (((")


def test_une_requete_vide_est_refusee() -> None:
    with pytest.raises(SqlRefuse):
        valider("   ")
