"""Point d'entree de l'API. Cree l'application et branche les routes."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.conversations import router as conversations_router
from app.api.dashboards import router as dashboards_router
from app.api.espaces import router as espaces_router
from app.api.finops import router as finops_router
from app.api.organisation import router as organisation_router
from app.api.plateforme import router as plateforme_router
from app.api.questions import router as questions_router
from app.api.sources import router as sources_router
from app.api.sources import router_connecteurs
from app.core.config import get_settings
from app.core.errors import ErreurUtilisateur


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

    @app.exception_handler(ErreurUtilisateur)
    async def gerer_erreur_utilisateur(_: Request, erreur: ErreurUtilisateur) -> JSONResponse:
        return JSONResponse(status_code=erreur.code_http, content={"detail": erreur.message})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(organisation_router)
    app.include_router(finops_router)
    app.include_router(espaces_router)
    app.include_router(router_connecteurs)
    app.include_router(sources_router)
    app.include_router(conversations_router)
    app.include_router(dashboards_router)
    app.include_router(questions_router)
    app.include_router(plateforme_router)

    return app


app = create_app()
