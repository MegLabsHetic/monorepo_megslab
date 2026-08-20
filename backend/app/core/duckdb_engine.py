"""Execution des requetes analytiques sur l'entrepot, via DuckDB.

Trois barrieres, independantes les unes des autres :

1. le SQL est valide et regenere par `sql_guard` avant d'arriver ici ;
2. l'entrepot est attache en LECTURE SEULE, et **restreint au schema de
   l'organisation** : une organisation ne peut pas nommer les tables d'une
   autre, elles ne sont simplement pas dans son catalogue ;
3. une fois l'entrepot attache, l'acces fichier et reseau du moteur est coupe
   et la configuration verrouillee, donc meme une requete qui aurait echappe
   au garde-fou ne peut ni lire un fichier ni sortir sur le reseau.

Chaque appel public ouvre **une** connexion en memoire et la referme : aucun
etat ne survit d'un appel a l'autre, et ouvrir l'entrepot coute assez cher
(quelques secondes) pour ne pas le faire trois fois dans la meme operation.
"""

import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import duckdb

from app.core.config import get_settings

logger = logging.getLogger(__name__)

NOM_ENTREPOT = "entrepot"
LIGNES_MAX = 5_000

# Colonnes de plomberie ajoutees par Airbyte dans chaque table synchronisee.
# Ce ne sont pas les donnees de l'utilisateur : on ne les montre pas.
PREFIXE_TECHNIQUE = "_airbyte_"


@dataclass(frozen=True)
class Resultat:
    """Le resultat d'une lecture : des colonnes, des lignes, et si on a coupe."""

    colonnes: list[str]
    lignes: list[tuple]
    tronque: bool

    @property
    def nb_lignes(self) -> int:
        return len(self.lignes)


_MOT_DE_PASSE_DSN = re.compile(r"password=\S+")


def _sans_secret(message: str) -> str:
    """Un message d'erreur qui cite le DSN cite aussi le mot de passe."""
    return _MOT_DE_PASSE_DSN.sub("password=***", message)


class ErreurRequete(Exception):
    """La requete n'a pas pu etre executee.

    `raison` est affichable a l'utilisateur. `detail` est le message brut du
    moteur : il ne s'affiche pas, mais l'Analyste en a besoin pour corriger sa
    requete — « n'a pas pu etre executee » ne dit pas quoi changer.
    """

    def __init__(self, raison: str, detail: str = "") -> None:
        super().__init__(raison)
        self.raison = raison
        self.detail = detail


@dataclass(frozen=True)
class ColonneProfil:
    nom: str
    type: str
    pourcentage_nuls: float
    distinctes_approx: int
    # Les valeurs exactes quand la colonne est une categorie (peu de valeurs
    # distinctes, courtes) ; None sinon.
    modalites: tuple[str, ...] | None


@dataclass(frozen=True)
class TableProfil:
    nom: str
    nb_lignes: int
    colonnes: tuple[ColonneProfil, ...]


# Au-dela de ce nombre de valeurs distinctes, une colonne texte n'est plus une
# categorie qu'on peut enumerer a un modele : c'est un identifiant ou du texte.
MODALITES_MAX = 12
LONGUEUR_MODALITE_MAX = 40


class DuckDBEngine:
    def __init__(self, schema_entrepot: str) -> None:
        self._schema = schema_entrepot

    @property
    def schema_entrepot(self) -> str:
        return self._schema

    # --- Operations publiques ---------------------------------------------

    def executer(self, sql_valide: str, lignes_max: int = LIGNES_MAX) -> Resultat:
        """Execute une requete DEJA validee par `sql_guard`.

        Ne jamais appeler avec du SQL brut : cette methode ne valide rien, elle
        se contente de verrouiller le moteur autour de ce qu'on lui donne.
        """
        with self._session() as connexion:
            return self._lire(connexion, sql_valide, lignes_max)

    def lister_tables(self) -> list[str]:
        """Les tables que cette organisation peut interroger."""
        with self._session() as connexion:
            return self._tables(connexion)

    def compter_lignes(self, table: str) -> int:
        with self._session() as connexion:
            nom = self._table_connue(connexion, table)
            resultat = self._lire(connexion, f'SELECT count(*) FROM {NOM_ENTREPOT}."{nom}"', 1)
            return int(resultat.lignes[0][0])

    def inventaire(self) -> list[tuple[str, int]]:
        """Chaque table avec son nombre de lignes, en une seule ouverture."""
        with self._session() as connexion:
            tables = self._tables(connexion)
            return [
                (
                    table,
                    int(
                        self._lire(
                            connexion, f'SELECT count(*) FROM {NOM_ENTREPOT}."{table}"', 1
                        ).lignes[0][0]
                    ),
                )
                for table in tables
            ]

    def schema(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """Chaque table avec ses colonnes visibles et leur type, en une seule ouverture.

        C'est ce qui part au modele pour qu'il ecrive du SQL : des noms et des
        types, jamais de donnees. Le type compte autant que le nom : une date
        que la synchronisation a deposee en VARCHAR ne se soustrait pas sans
        conversion, et le modele ne peut le savoir que si on le lui dit.
        """
        with self._session() as connexion:
            return [
                (table, self._colonnes_typees(connexion, table))
                for table in self._tables(connexion)
            ]

    def apercu(self, table: str, limite: int = 50) -> Resultat:
        """Les premieres lignes reelles d'une table, colonnes techniques exclues."""
        with self._session() as connexion:
            nom = self._table_connue(connexion, table)
            colonnes = self._colonnes_visibles(connexion, nom)
            if not colonnes:
                return Resultat(colonnes=[], lignes=[], tronque=False)

            projection = ", ".join(f'"{colonne}"' for colonne in colonnes)
            return self._lire(
                connexion,
                f'SELECT {projection} FROM {NOM_ENTREPOT}."{nom}" LIMIT {int(limite)}',
                limite,
            )

    def profiler(self, table: str) -> list[dict]:
        """Un profil par colonne : type, valeurs manquantes, distinctes, bornes.

        `SUMMARIZE` fait ce calcul dans le moteur plutot que de rapatrier la
        table pour la profiler en Python.
        """
        with self._session() as connexion:
            nom = self._table_connue(connexion, table)
            visibles = set(self._colonnes_visibles(connexion, nom))
            resultat = self._lire(connexion, f'SUMMARIZE {NOM_ENTREPOT}."{nom}"', LIGNES_MAX)

        profils = [dict(zip(resultat.colonnes, ligne)) for ligne in resultat.lignes]
        return [profil for profil in profils if profil.get("column_name") in visibles]

    def profil_complet(self) -> list[TableProfil]:
        """Toutes les tables avec effectif, colonnes typees et modalites, en une ouverture.

        C'est ce que l'agent Data transmet aux agents qui ecrivent du SQL. Une
        seule session pour tout : ouvrir l'entrepot coute des secondes, et il y
        a une requete de profil par table plus une par colonne categorielle.
        """
        with self._session() as connexion:
            return [self._profil_table(connexion, table) for table in self._tables(connexion)]

    # --- Interieur ---------------------------------------------------------

    def _profil_table(self, connexion: duckdb.DuckDBPyConnection, table: str) -> TableProfil:
        resume = self._lire(connexion, f'SUMMARIZE {NOM_ENTREPOT}."{table}"', LIGNES_MAX)
        lignes = [dict(zip(resume.colonnes, ligne)) for ligne in resume.lignes]
        nb_lignes = int(lignes[0]["count"]) if lignes else 0
        colonnes = [
            self._profil_colonne(connexion, table, ligne)
            for ligne in lignes
            if not str(ligne["column_name"]).startswith(PREFIXE_TECHNIQUE)
        ]
        return TableProfil(nom=table, nb_lignes=nb_lignes, colonnes=tuple(colonnes))

    def _profil_colonne(
        self, connexion: duckdb.DuckDBPyConnection, table: str, ligne: dict
    ) -> ColonneProfil:
        nom, type_ = str(ligne["column_name"]), str(ligne["column_type"])
        distinctes = int(ligne["approx_unique"] or 0)
        modalites = None
        if type_ == "VARCHAR" and 0 < distinctes <= MODALITES_MAX:
            modalites = self._modalites(connexion, table, nom)
        return ColonneProfil(
            nom=nom,
            type=type_,
            pourcentage_nuls=float(ligne["null_percentage"] or 0),
            distinctes_approx=distinctes,
            modalites=modalites,
        )

    def _modalites(
        self, connexion: duckdb.DuckDBPyConnection, table: str, colonne: str
    ) -> tuple[str, ...] | None:
        """`approx_unique` est une estimation : on relit les valeurs exactes et on
        renonce si elles debordent ou si ce sont des textes longs."""
        resultat = self._lire(
            connexion,
            f'SELECT DISTINCT "{colonne}" FROM {NOM_ENTREPOT}."{table}" '
            f'WHERE "{colonne}" IS NOT NULL ORDER BY 1 LIMIT {MODALITES_MAX + 1}',
            MODALITES_MAX + 1,
        )
        valeurs = [str(ligne[0]) for ligne in resultat.lignes]
        if len(valeurs) > MODALITES_MAX or any(len(v) > LONGUEUR_MODALITE_MAX for v in valeurs):
            return None
        return tuple(valeurs)

    def _lire(self, connexion: duckdb.DuckDBPyConnection, sql: str, lignes_max: int) -> Resultat:
        try:
            curseur = connexion.execute(sql)
            colonnes = [description[0] for description in curseur.description or []]
            lignes = curseur.fetchmany(lignes_max + 1)
        except duckdb.Error as erreur:
            # Jamais logger.exception ici : une connexion perdue en cours de
            # requete produit une IOException qui cite le DSN, mot de passe
            # compris. Message masque, chainage coupe.
            logger.error(
                "Echec d'execution DuckDB sur le schema %s : %s",
                self._schema,
                _sans_secret(str(erreur)),
            )
            raise ErreurRequete(
                self._message_lisible(erreur), detail=_sans_secret(str(erreur))
            ) from None

        tronque = len(lignes) > lignes_max
        return Resultat(colonnes=colonnes, lignes=lignes[:lignes_max], tronque=tronque)

    def _tables(self, connexion: duckdb.DuckDBPyConnection) -> list[str]:
        try:
            lignes = connexion.execute(
                "select table_name from duckdb_tables() "
                "where database_name = ? order by table_name",
                [NOM_ENTREPOT],
            ).fetchall()
        except duckdb.Error as erreur:
            logger.error(
                "Echec de listage des tables du schema %s : %s",
                self._schema,
                _sans_secret(str(erreur)),
            )
            raise ErreurRequete(self._message_lisible(erreur)) from None
        return [nom for (nom,) in lignes]

    def _colonnes_visibles(self, connexion: duckdb.DuckDBPyConnection, table: str) -> list[str]:
        return [nom for nom, _ in self._colonnes_typees(connexion, table)]

    def _colonnes_typees(
        self, connexion: duckdb.DuckDBPyConnection, table: str
    ) -> list[tuple[str, str]]:
        try:
            lignes = connexion.execute(
                "select column_name, data_type from duckdb_columns() "
                "where database_name = ? and table_name = ? order by column_index",
                [NOM_ENTREPOT, table],
            ).fetchall()
        except duckdb.Error as erreur:
            logger.error(
                "Echec de lecture des colonnes de %s : %s", table, _sans_secret(str(erreur))
            )
            raise ErreurRequete(self._message_lisible(erreur)) from None
        return [(nom, type_) for nom, type_ in lignes if not nom.startswith(PREFIXE_TECHNIQUE)]

    def _table_connue(self, connexion: duckdb.DuckDBPyConnection, table: str) -> str:
        """Le nom de table vient de l'utilisateur : il ne sert a construire une
        requete qu'apres avoir ete retrouve dans le catalogue de l'organisation.
        Aucun echappement a inventer, et rien hors de son schema n'est nommable."""
        if table in self._tables(connexion):
            return table
        raise ErreurRequete(f"La table « {table} » n'existe pas dans vos donnees.")

    # --- Verrouillage du moteur ------------------------------------------

    @contextmanager
    def _session(self) -> Iterator[duckdb.DuckDBPyConnection]:
        connexion = self._connexion_verrouillee()
        try:
            yield connexion
        finally:
            connexion.close()

    def _connexion_verrouillee(self) -> duckdb.DuckDBPyConnection:
        connexion = duckdb.connect(":memory:")
        try:
            connexion.execute("INSTALL postgres; LOAD postgres;")
            connexion.execute(
                f"ATTACH '{self._dsn()}' AS {NOM_ENTREPOT} "
                f"(TYPE postgres, READ_ONLY, SCHEMA '{self._schema}')"
            )
            # Apres l'attache seulement : l'extension postgres a besoin du
            # reseau pour se connecter, la requete de l'utilisateur non.
            connexion.execute("SET enable_external_access=false")
            connexion.execute("SET lock_configuration=true")
        except duckdb.Error as erreur:
            connexion.close()
            # Pas de logger.exception ici : le message de DuckDB reprend le DSN
            # complet, mot de passe compris. On le masque, et on coupe le
            # chainage pour qu'aucune trace en amont ne le reimprime.
            logger.error(
                "Echec d'ouverture de l'entrepot pour le schema %s : %s",
                self._schema,
                _sans_secret(str(erreur)),
            )
            raise ErreurRequete(
                "L'entrepot de donnees n'est pas joignable pour le moment."
            ) from None
        return connexion

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
        """Le detail technique reste dans les logs ; l'utilisateur recoit une phrase.

        On distingue quand meme le cas le plus frequent — une colonne ou une
        table qui n'existe pas — parce que la reponse utile n'est pas la meme.
        """
        texte = str(erreur).lower()
        if "does not exist" in texte or "not found" in texte or "referenced column" in texte:
            return "Cette requete fait reference a une table ou une colonne qui n'existe pas."
        return "Cette requete n'a pas pu etre executee sur vos donnees."
