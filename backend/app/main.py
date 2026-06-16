"""Point d'entree de l'API. Cree l'application et branche les routes."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings


def create_app() -> FastAPI:
    """Construit l'application FastAPI, prete a etre servie par uvicorn."""
    reglages = get_settings()
    app = FastAPI(title="MegLabs API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=reglages.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
