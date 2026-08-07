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

    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./data/megslab.db"

    # Vide par defaut : get_settings() genere un secret ephemere si absent, pour
    # qu'un oubli en dev ne signe jamais les jetons avec une chaine vide.
    jwt_secret: str = ""

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""

    airbyte_base_url: str = ""
    airbyte_client_id: str = ""
    airbyte_client_secret: str = ""

    # Entrepot partage : chaque organisation y a son propre schema (voir
    # OrganizationService), pas sa propre base. Adresse jointe par Airbyte
    # (reseau "kind" du cluster), pas par le backend lui-meme pour l'instant.
    warehouse_postgres_host: str = ""
    warehouse_postgres_port: int = 5432
    warehouse_postgres_database: str = ""
    warehouse_postgres_username: str = ""
    warehouse_postgres_password: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origine.strip() for origine in self.cors_origins.split(",") if origine.strip()]


@lru_cache
def get_settings() -> Settings:
    """Point d'entree unique pour lire la configuration.

    Mise en cache volontaire : l'environnement ne change pas en cours de vie du
    processus, pas besoin de relire le fichier .env a chaque appel. Ca permet
    aussi au secret JWT ephemere ci-dessous de rester stable pendant la vie du
    processus, meme s'il n'est pas fourni.
    """
    reglages = Settings()
    if not reglages.jwt_secret:
        reglages.jwt_secret = secrets.token_hex(32)
    return reglages
