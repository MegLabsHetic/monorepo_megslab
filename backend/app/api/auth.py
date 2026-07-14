"""Routes d'authentification : inscription, connexion, profil courant."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import utilisateur_courant
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ConnexionDemande,
    InscriptionDemande,
    SessionReponse,
    UtilisateurReponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/inscription", response_model=UtilisateurReponse, status_code=201)
async def inscription(demande: InscriptionDemande, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    return await service.inscrire(demande.email, demande.mot_de_passe, demande.nom_complet)


@router.post("/connexion", response_model=SessionReponse)
async def connexion(demande: ConnexionDemande, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    jeton = await service.connecter(demande.email, demande.mot_de_passe)
    return SessionReponse(jeton=jeton)


@router.get("/moi", response_model=UtilisateurReponse)
async def moi(utilisateur: User = Depends(utilisateur_courant)):
    return utilisateur
