"""Execution des requetes analytiques sur l'entrepot, via DuckDB.

Trois barrieres, independantes les unes des autres :

1. le SQL est valide et regenere par `sql_guard` avant d'arriver ici ;
2. l'entrepot est attache en LECTURE SEULE, et **restreint au schema de
   l'organisation** : une organisation ne peut pas nommer les tables d'une
   autre, elles ne sont simplement pas dans son catalogue ;
3. une fois l'entrepot attache, l'acces fichier et reseau du moteur est coupe
   et la configuration verrouillee, donc meme une requete qui aurait echappe
   au garde-fou ne peut ni lire un fichier ni sortir sur le reseau.

Chaque requete ouvre sa propre connexion en memoire et la referme : aucun etat
ne survit d'une requete a l'autre.
"""

import logging
from dataclasses import dataclass

import duckdb

from app.core.config import get_settings

logger = logging.getLogger(__name__)

NOM_ENTREPOT = "entrepot"
LIGNES_MAX = 5_000


@dataclass(frozen=True)
class Resultat:
    """Le resultat d'une lecture : des colonnes, des lignes, et si on a coupe."""

    colonnes: list[str]
    lignes: list[tuple]
    tronque: bool

    @property
    def nb_lignes(self) -> int:
        return len(self.lignes)


class ErreurRequete(Exception):
    """La requete n'a pas pu etre executee. `raison` est affichable."""

    def __init__(self, raison: str) -> None:
        super().__init__(raison)
        self.raison = raison


class DuckDBEngine:
    def __init__(self, schema_entrepot: str) -> None:
        self._schema = schema_entrepot

    def executer(self, sql_valide: str, lignes_max: int = LIGNES_MAX) -> Resultat:
        """Execute une requete DEJA validee par `sql_guard`.

        Ne jamais appeler avec du SQL brut : cette methode ne valide rien, elle
        se contente de verrouiller le moteur autour de ce qu'on lui donne.
        """
        connexion = self._connexion_verrouillee()
        try:
            curseur = connexion.execute(sql_valide)
            colonnes = [description[0] for description in curseur.description or []]
            lignes = curseur.fetchmany(lignes_max + 1)
        except duckdb.Error as erreur:
            logger.exception("Echec d'execution DuckDB sur le schema %s", self._schema)
            raise ErreurRequete(self._message_lisible(erreur)) from erreur
        finally:
            connexion.close()

        tronque = len(lignes) > lignes_max
        return Resultat(colonnes=colonnes, lignes=lignes[:lignes_max], tronque=tronque)

    def lister_tables(self) -> list[str]:
        """Les tables que cette organisation peut interroger."""
        connexion = self._connexion_verrouillee()
        try:
            resultat = connexion.execute(
                "select table_name from duckdb_tables() "
                "where database_name = ? order by table_name",
                [NOM_ENTREPOT],
            ).fetchall()
        except duckdb.Error as erreur:
            logger.exception("Echec de listage des tables du schema %s", self._schema)
            raise ErreurRequete(self._message_lisible(erreur)) from erreur
        finally:
            connexion.close()
        return [ligne[0] for ligne in resultat]

    # --- Verrouillage du moteur ------------------------------------------

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
            logger.exception("Echec d'ouverture de l'entrepot pour le schema %s", self._schema)
            raise ErreurRequete(
                "L'entrepot de donnees n'est pas joignable pour le moment."
            ) from erreur
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
