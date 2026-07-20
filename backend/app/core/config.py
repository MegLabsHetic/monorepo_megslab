"""Configuration de l'application, lue une fois depuis l'environnement."""

import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables d'environnement du backend, avec des valeurs par defaut sures."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./data/megslab.db"

    # Vide par defaut : get_settings() genere un secret ephemere si absent, pour
    # qu'un oubli en dev ne signe jamais les jetons avec une chaine vide.
    jwt_secret: str = ""

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""

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
