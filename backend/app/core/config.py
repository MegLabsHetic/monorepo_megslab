"""Configuration de l'application, lue une fois depuis l'environnement."""

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Le .env vit a la racine du depot, pas dans backend/. Un chemin relatif au
# repertoire courant casse des qu'on lance uvicorn depuis backend/ (le cas
# local le plus courant) : on resout depuis l'emplacement de ce fichier a la
# place. Docker Compose n'en a pas besoin, il injecte deja de vraies variables
# d'environnement, silencieusement ignorees si ce fichier n'existe pas.
_RACINE_DEPOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Variables d'environnement du backend, avec des valeurs par defaut sures."""

    model_config = SettingsConfigDict(env_file=_RACINE_DEPOT / ".env", extra="ignore")

    # « production » durcit le demarrage : voir `_exiger_les_secrets`. Toute
    # autre valeur est traitee comme un poste de developpement.
    environnement: str = "developpement"

    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./data/megslab.db"

    # Vide par defaut : get_settings() genere un secret ephemere si absent, pour
    # qu'un oubli en dev ne signe jamais les jetons avec une chaine vide.
    jwt_secret: str = ""

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""

    airbyte_base_url: str = ""
    # L'URL que le navigateur de l'utilisateur peut atteindre. Elle differe
    # de airbyte_base_url des que le backend passe par un reseau interne.
    airbyte_url_publique: str = ""
    airbyte_client_id: str = ""
    airbyte_client_secret: str = ""

    # Entrepot partage : chaque organisation y a son propre schema (voir
    # OrganizationService), pas sa propre base.
    #
    # Deux adresses pour la meme base, parce que deux clients differents y
    # accedent : Airbyte y ECRIT depuis le reseau Docker du cluster, le backend
    # y LIT de l'exterieur (tunnel SSH en developpement, adresse interne une
    # fois le backend deploye a cote). Les confondre casserait l'un ou l'autre.
    warehouse_postgres_host: str = ""
    warehouse_postgres_port: int = 5432
    warehouse_postgres_database: str = ""
    warehouse_postgres_username: str = ""
    warehouse_postgres_password: str = ""

    warehouse_lecture_host: str = "127.0.0.1"
    warehouse_lecture_port: int = 55433

    # Le schema de l'entrepot qui contient le jeu de demonstration a copier
    # dans un espace en un clic. Vide : la fonctionnalite n'est pas proposee.
    demo_schema: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origine.strip() for origine in self.cors_origins.split(",") if origine.strip()]

    @property
    def en_production(self) -> bool:
        return self.environnement.strip().lower() == "production"


class ConfigurationIncomplete(RuntimeError):
    """Un secret indispensable manque. Leve au demarrage, jamais en cours de requete."""


def _exiger_les_secrets(reglages: Settings) -> None:
    """Refuse de demarrer en production avec une configuration a trous.

    Un secret JWT genere a la volee parait fonctionner : chaque redemarrage
    deconnecte tout le monde, et deux instances ne reconnaissent pas les jetons
    l'une de l'autre. La panne est silencieuse et intermittente, donc chere a
    diagnostiquer. Mieux vaut ne pas demarrer du tout.
    """
    manquants = [
        nom
        for nom, valeur in (
            ("JWT_SECRET", reglages.jwt_secret),
            ("WAREHOUSE_POSTGRES_DATABASE", reglages.warehouse_postgres_database),
            ("WAREHOUSE_POSTGRES_USERNAME", reglages.warehouse_postgres_username),
            ("WAREHOUSE_POSTGRES_PASSWORD", reglages.warehouse_postgres_password),
        )
        if not valeur
    ]
    if manquants:
        raise ConfigurationIncomplete(
            "Demarrage refuse : ces variables d'environnement sont vides alors que "
            f"ENVIRONNEMENT=production : {', '.join(manquants)}."
        )


@lru_cache
def get_settings() -> Settings:
    """Point d'entree unique pour lire la configuration.

    Mise en cache volontaire : l'environnement ne change pas en cours de vie du
    processus, pas besoin de relire le fichier .env a chaque appel. Ca permet
    aussi au secret JWT ephemere ci-dessous de rester stable pendant la vie du
    processus, meme s'il n'est pas fourni.
    """
    reglages = Settings()
    if reglages.en_production:
        _exiger_les_secrets(reglages)
    elif not reglages.jwt_secret:
        # Developpement seulement : un oubli ne doit jamais signer les jetons
        # avec une chaine vide. En production, on refuse de demarrer.
        reglages.jwt_secret = secrets.token_hex(32)
    return reglages
