"""Verification qu'une requete SQL est bien une lecture, et rien d'autre.

Deux principes.

**Liste blanche, pas liste noire.** On n'enumere pas ce qui est interdit (une
liste noire se contourne toujours : commentaires, encodage, syntaxe exotique) :
on n'autorise qu'un seul type d'arbre, celui d'une lecture. Tout le reste est
refuse par defaut, y compris ce qu'on n'a pas anticipe.

**On execute l'arbre, pas le texte.** La requete finalement executee est
regeneree depuis l'arbre valide. Ce qui n'a pas ete compris et valide par
l'analyseur ne peut donc pas atteindre le moteur.

Ce garde-fou n'est pas seul : le moteur DuckDB est lui-meme verrouille
(lecture seule, acces fichier et reseau desactives). Voir `duckdb_engine`.
"""

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

DIALECTE = "duckdb"

# Les seules racines acceptees : une lecture, eventuellement avec des CTE
# (`WITH`, porte par l'expression elle-meme) ou un operateur ensembliste.
RACINES_AUTORISEES = (exp.Select, exp.Union, exp.Except, exp.Intersect, exp.Subquery)

# Fonctions DuckDB qui lisent un fichier ou le reseau. Le moteur les bloque
# deja ; on les refuse aussi ici pour rendre le refus explicite et donner un
# message clair plutot qu'une erreur de permission opaque.
FONCTIONS_INTERDITES = frozenset(
    {
        "read_csv",
        "read_csv_auto",
        "read_parquet",
        "read_json",
        "read_json_auto",
        "read_ndjson",
        "read_ndjson_auto",
        "read_text",
        "read_blob",
        "parquet_scan",
        "csv_scan",
        "glob",
        "sniff_csv",
        "postgres_scan",
        "postgres_query",
        "postgres_execute",
        "postgres_attach",
        "sqlite_scan",
        "mysql_scan",
        "mysql_query",
        "iceberg_scan",
        "delta_scan",
    }
)


class SqlRefuse(Exception):
    """La requete n'est pas une lecture acceptable. `raison` est affichable."""

    def __init__(self, raison: str) -> None:
        super().__init__(raison)
        self.raison = raison


def valider(sql: str) -> str:
    """Renvoie le SQL regenere depuis l'arbre valide, ou leve `SqlRefuse`."""
    expression = _analyser(sql)
    _refuser_si_pas_une_lecture(expression)
    _refuser_les_fonctions_interdites(expression)
    # `comments=False` : rien du texte d'origine ne survit a la regeneration.
    return expression.sql(dialect=DIALECTE, comments=False)


def _analyser(sql: str) -> exp.Expression:
    try:
        expressions = sqlglot.parse(sql, dialect=DIALECTE)
    except SqlglotError as erreur:
        # SqlglotError couvre l'analyse ET la tokenisation : une requete
        # illisible ne doit jamais remonter en exception non geree.
        raise SqlRefuse("Cette requete n'est pas du SQL valide.") from erreur

    expressions = [e for e in expressions if e is not None]
    if not expressions:
        raise SqlRefuse("Aucune requete a executer.")
    if len(expressions) > 1:
        # Sinon `SELECT 1; DROP TABLE t` passerait sur la foi de sa premiere moitie.
        raise SqlRefuse("Une seule requete a la fois.")
    return expressions[0]


def _refuser_si_pas_une_lecture(expression: exp.Expression) -> None:
    if not isinstance(expression, RACINES_AUTORISEES):
        raise SqlRefuse(
            "Seules les requetes de lecture (SELECT) sont autorisees : "
            f"celle-ci est un {type(expression).__name__.upper()}."
        )

    # Une lecture peut cacher une ecriture dans une sous-requete ou une CTE.
    for noeud in expression.walk():
        if isinstance(noeud, RACINES_AUTORISEES):
            continue
        if isinstance(noeud, (exp.DDL, exp.DML, exp.Command)):
            raise SqlRefuse("Cette requete contient une operation qui n'est pas une lecture.")


def _refuser_les_fonctions_interdites(expression: exp.Expression) -> None:
    for noeud in expression.find_all(exp.Func):
        nom = _nom_de_fonction(noeud)
        if nom in FONCTIONS_INTERDITES:
            raise SqlRefuse(
                f"La fonction « {nom} » lit des fichiers ou le reseau : elle n'est pas autorisee."
            )


def _nom_de_fonction(noeud: exp.Func) -> str:
    """Le nom ecrit dans la requete pour une fonction inconnue de l'analyseur,
    son nom canonique sinon."""
    if isinstance(noeud, exp.Anonymous):
        return str(noeud.this).lower()
    return noeud.sql_name().lower()
