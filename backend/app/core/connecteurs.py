"""Les connecteurs de bases de donnees que MegLabs sait configurer.

Chaque entree traduit un formulaire d'identifiants (hote, port, base, compte)
en configuration Airbyte. Ces formes n'ont pas ete devinees : elles ont ete
obtenues en soumettant des configurations incompletes a l'instance Airbyte et
en lisant ses erreurs de validation.

Piege verifie de cette maniere : PostgreSQL attend `"Standard"`, tandis que
MySQL et SQL Server attendent `"STANDARD"` en majuscules. Une seule constante
partagee casserait deux connecteurs sur trois.
"""

from dataclasses import dataclass

SANS_TUNNEL = {"tunnel_method": "NO_TUNNEL"}


@dataclass(frozen=True)
class Connecteur:
    """Un type de base que l'utilisateur peut brancher."""

    cle: str
    libelle: str
    source_type: str
    port_defaut: int
    methode_replication: str
    # PostgreSQL veut savoir quels schemas lire ; MySQL et SQL Server non, la
    # base suffit a les delimiter.
    demande_schemas: bool = False

    def configuration(
        self, host: str, port: int, database: str, username: str, mot_de_passe: str
    ) -> dict:
        config = {
            "sourceType": self.source_type,
            "host": host,
            "port": port,
            "database": database,
            "username": username,
            "password": mot_de_passe,
            "replication_method": {"method": self.methode_replication},
            "tunnel_method": SANS_TUNNEL,
        }
        if self.demande_schemas:
            config["schemas"] = ["public"]
            config["ssl_mode"] = {"mode": "disable"}
        return config


CONNECTEURS = {
    connecteur.cle: connecteur
    for connecteur in (
        Connecteur(
            cle="postgres",
            libelle="PostgreSQL",
            source_type="postgres",
            port_defaut=5432,
            methode_replication="Standard",
            demande_schemas=True,
        ),
        Connecteur(
            cle="mysql",
            libelle="MySQL",
            source_type="mysql",
            port_defaut=3306,
            methode_replication="STANDARD",
        ),
        Connecteur(
            cle="mssql",
            libelle="SQL Server",
            source_type="mssql",
            port_defaut=1433,
            methode_replication="STANDARD",
        ),
    )
}


def connecteur(cle: str) -> Connecteur:
    if cle not in CONNECTEURS:
        connus = ", ".join(sorted(CONNECTEURS))
        raise ValueError(f"Type de source inconnu : {cle}. Types connus : {connus}.")
    return CONNECTEURS[cle]
