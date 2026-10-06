"""Prepare le schema de demonstration de l'entrepot a partir de tables existantes.

Copie, cote Postgres, les tables d'un schema qui portent un prefixe donne
vers un schema de demonstration, sans le prefixe. A lancer une fois, puis
renseigner DEMO_SCHEMA dans le .env.

    python -m app.scripts.preparer_demo org_<id> se49b598f_ demo_olist
"""

import re
import sys

import duckdb

from app.core.entrepot_writer import EntrepotWriter, _executer_dans_postgres


def _preparer(schema_source: str, prefixe: str, schema_demo: str) -> None:
    dsn = EntrepotWriter(schema_source)._dsn()
    connexion = duckdb.connect(":memory:")
    try:
        connexion.execute("INSTALL postgres; LOAD postgres;")
        connexion.execute(f"ATTACH '{dsn}' AS entrepot (TYPE postgres)")
        tables = [
            nom
            for (nom,) in connexion.execute(
                "select table_name from duckdb_tables() "
                "where database_name = 'entrepot' and schema_name = ? order by table_name",
                [schema_source],
            ).fetchall()
            if nom.startswith(prefixe)
        ]
        if not tables:
            print(f"Aucune table prefixee « {prefixe} » dans {schema_source}.")
            sys.exit(1)
        _executer_dans_postgres(connexion, f'CREATE SCHEMA IF NOT EXISTS "{schema_demo}"')
        for table in tables:
            cible = table[len(prefixe) :]
            _executer_dans_postgres(connexion, f'DROP TABLE IF EXISTS "{schema_demo}"."{cible}"')
            _executer_dans_postgres(
                connexion,
                f'CREATE TABLE "{schema_demo}"."{cible}" AS TABLE "{schema_source}"."{table}"',
            )
            print(f"  {table} -> {schema_demo}.{cible}")
        print(
            f"{len(tables)} table(s) copiee(s). Renseignez DEMO_SCHEMA={schema_demo} dans le .env."
        )
    except duckdb.Error as erreur:
        print("Echec :", re.sub(r"password=\S+", "password=***", str(erreur))[:300])
        sys.exit(1)
    finally:
        connexion.close()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    _preparer(sys.argv[1], sys.argv[2], sys.argv[3])
