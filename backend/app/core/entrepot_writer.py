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
from app.core.duckdb_engine import PREFIXE_TECHNIQUE

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


def _executer_dans_postgres(connexion: duckdb.DuckDBPyConnection, sql: str) -> None:
    """Fait executer une instruction par Postgres lui-meme, via la base attachee.

    Les identifiants viennent du catalogue de l'entrepot ou de nos propres
    constantes, jamais d'une saisie : c'est la seule raison pour laquelle
    cette porte reste ouverte au writer, et fermee au moteur de lecture.
    """
    connexion.execute(f"CALL postgres_execute('entrepot', '{sql.replace(chr(39), chr(39) * 2)}')")


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

    def copier_tables(
        self, schema_source: str, tables: list[str], prefixe: str
    ) -> dict[str, list[str]]:
        """Copie des tables d'un autre schema de l'entrepot dans celui-ci, par Postgres.

        Rend les colonnes de chaque table copiee, comme `importer`. Les noms
        viennent du catalogue de l'entrepot, jamais d'une saisie.
        """
        connexion = duckdb.connect(":memory:")
        colonnes: dict[str, list[str]] = {}
        try:
            connexion.execute("INSTALL postgres; LOAD postgres;")
            connexion.execute(f"ATTACH '{self._dsn()}' AS entrepot (TYPE postgres)")
            connexion.execute(f'CREATE SCHEMA IF NOT EXISTS entrepot."{self._schema}"')
            for table in tables:
                # La copie est faite PAR Postgres : rien ne transite par ici.
                # Faire lire puis reecrire un million de lignes par DuckDB a
                # travers le reseau prendrait des minutes ; cote serveur, des secondes.
                origine = f'"{schema_source}"."{table}"'
                cible = f'"{self._schema}"."{prefixe}{table}"'
                _executer_dans_postgres(connexion, f"DROP TABLE IF EXISTS {cible}")
                _executer_dans_postgres(connexion, f"CREATE TABLE {cible} AS TABLE {origine}")
                # Les colonnes sont lues sur la table SOURCE, pas sur la copie :
                # « CREATE TABLE ... AS TABLE » les reproduit a l'identique, et le
                # catalogue attache ne voit pas les tables creees derriere son dos.
                # Les colonnes techniques d'Airbyte ne sont pas du metier : une
                # source connectee ne les montre pas non plus.
                colonnes[table] = [
                    nom
                    for (nom,) in connexion.execute(
                        "select column_name from duckdb_columns() "
                        "where database_name = 'entrepot' and schema_name = ? and table_name = ? "
                        "order by column_index",
                        [schema_source, table],
                    ).fetchall()
                    if not nom.startswith(PREFIXE_TECHNIQUE)
                ]
                if not colonnes[table]:
                    raise ErreurImport(f"La table « {table} » est introuvable dans le jeu source.")
        except duckdb.Error as erreur:
            logger.error(
                "Echec de copie du schema %s vers %s : %s",
                schema_source,
                self._schema,
                re.sub(r"password=\S+", "password=***", str(erreur))[:300],
            )
            raise ErreurImport("L'entrepot n'a pas pu copier le jeu de demonstration.") from None
        finally:
            connexion.close()
        return colonnes

    def supprimer_tables(self, tables: list[str]) -> None:
        """Fait tomber les tables d'une source dans l'entrepot. Les noms viennent
        de ce que MegsLab a lui-meme enregistre a la synchronisation, jamais
        d'une saisie."""
        connexion = duckdb.connect(":memory:")
        try:
            connexion.execute("INSTALL postgres; LOAD postgres;")
            connexion.execute(f"ATTACH '{self._dsn()}' AS entrepot (TYPE postgres)")
            for table in tables:
                nom = table.replace('"', '""')
                connexion.execute(f'DROP TABLE IF EXISTS entrepot."{self._schema}"."{nom}"')
        except duckdb.Error as erreur:
            # Pas de trace complete : le message d'attache cite le DSN, mot de passe compris.
            logger.error(
                "Echec de suppression de tables dans %s : %s",
                self._schema,
                re.sub(r"password=\S+", "password=***", str(erreur))[:300],
            )
            raise ErreurImport(
                "L'entrepot n'a pas pu supprimer les tables de cette source."
            ) from None
        finally:
            connexion.close()

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
