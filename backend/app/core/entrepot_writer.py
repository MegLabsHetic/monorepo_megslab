"""Import d'un fichier depose directement dans l'entrepot.

Ce chemin ne passe pas par Airbyte : Airbyte relie des systemes externes, pas
un fichier qu'un utilisateur vient de deposer. DuckDB lit le CSV ou le XLSX,
en deduit les types, et ecrit la table dans le schema de l'organisation.

La connexion utilisee ici est volontairement DISTINCTE de celle de
`DuckDBEngine` : ce moteur-la a l'acces fichier coupe et l'entrepot en lecture
seule, ce qui est exactement l'inverse de ce dont un import a besoin. Les deux
ne doivent jamais etre confondus — l'un execute du SQL venu d'un modele, celui-ci
ne lit qu'un fichier que nous venons nous-memes d'ecrire sur disque.
"""

import logging
import re
from pathlib import Path

import duckdb

from app.core.config import get_settings

logger = logging.getLogger(__name__)

EXTENSIONS_ACCEPTEES = {".csv", ".xlsx"}
LIGNES_MAX_IMPORT = 1_000_000


class ErreurImport(Exception):
    """L'import a echoue. `raison` est affichable telle quelle."""

    def __init__(self, raison: str) -> None:
        super().__init__(raison)
        self.raison = raison


def nom_de_table(nom_fichier: str) -> str:
    """Transforme un nom de fichier en nom de table utilisable.

    « Ventes Q1 2026.csv » devient « ventes_q1_2026 ». Le resultat ne contient
    que des minuscules, des chiffres et des tirets bas : il n'y a donc rien a
    echapper quand il sert ensuite a construire un CREATE TABLE.
    """
    base = Path(nom_fichier).stem.lower()
    nettoye = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    if not nettoye or nettoye[0].isdigit():
        nettoye = f"t_{nettoye}"
    return nettoye[:48]


class EntrepotWriter:
    def __init__(self, schema_entrepot: str) -> None:
        self._schema = schema_entrepot

    def importer(self, fichier: Path, table: str) -> tuple[int, list[str]]:
        """Copie le fichier dans l'entrepot.

        Rend le nombre de lignes ecrites et les colonnes telles que le moteur
        les a deduites — la fiche de la source en a besoin pour afficher son
        schema, exactement comme pour une base connectee.
        """
        extension = fichier.suffix.lower()
        if extension not in EXTENSIONS_ACCEPTEES:
            raise ErreurImport(f"Le format « {extension} » n'est pas pris en charge.")

        lecture = self._expression_de_lecture(fichier, extension)
        connexion = duckdb.connect(":memory:")
        try:
            connexion.execute("INSTALL postgres; LOAD postgres;")
            if extension == ".xlsx":
                connexion.execute("INSTALL excel; LOAD excel;")
            connexion.execute(f"ATTACH '{self._dsn()}' AS entrepot (TYPE postgres)")
            connexion.execute(f'CREATE SCHEMA IF NOT EXISTS entrepot."{self._schema}"')
            connexion.execute(f'DROP TABLE IF EXISTS entrepot."{self._schema}"."{table}"')
            connexion.execute(
                f'CREATE TABLE entrepot."{self._schema}"."{table}" AS '
                f"SELECT * FROM {lecture} LIMIT {LIGNES_MAX_IMPORT}"
            )
            (lignes,) = connexion.execute(
                f'SELECT count(*) FROM entrepot."{self._schema}"."{table}"'
            ).fetchone()
            colonnes = [
                nom
                for (nom,) in connexion.execute(
                    "select column_name from duckdb_columns() "
                    "where database_name = 'entrepot' and schema_name = ? and table_name = ? "
                    "order by column_index",
                    [self._schema, table],
                ).fetchall()
            ]
        except duckdb.Error as erreur:
            logger.exception("Echec d'import du fichier %s dans %s", fichier.name, self._schema)
            raise ErreurImport(self._message_lisible(erreur)) from erreur
        finally:
            connexion.close()

        return int(lignes), colonnes

    @staticmethod
    def _expression_de_lecture(fichier: Path, extension: str) -> str:
        """Le chemin est celui d'un fichier que NOUS venons d'ecrire dans un
        repertoire temporaire, jamais une valeur fournie par l'utilisateur."""
        chemin = str(fichier).replace("\\", "/")
        if extension == ".csv":
            return f"read_csv('{chemin}', header = true, sample_size = 20000)"
        return f"read_xlsx('{chemin}', header = true)"

    def _dsn(self) -> str:
        reglages = get_settings()
        return (
            f"host={reglages.warehouse_lecture_host} "
            f"port={reglages.warehouse_lecture_port} "
            f"dbname={reglages.warehouse_postgres_database} "
            f"user={reglages.warehouse_postgres_username} "
            f"password={reglages.warehouse_postgres_password}"
        )

    @staticmethod
    def _message_lisible(erreur: duckdb.Error) -> str:
        texte = str(erreur).lower()
        if "invalid input error" in texte or "csv error" in texte or "sniff" in texte:
            return (
                "Ce fichier n'a pas pu etre lu. Verifiez qu'il s'agit bien d'un CSV "
                "ou d'un XLSX avec une ligne d'en-tetes."
            )
        return "Ce fichier n'a pas pu etre importe dans l'entrepot."
