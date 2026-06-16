"""Configuration de l'application, lue une fois depuis l'environnement."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables d'environnement du backend, avec des valeurs par defaut sures."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./data/megslab.db"

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
    processus, pas besoin de relire le fichier .env a chaque appel.
    """
    return Settings()
