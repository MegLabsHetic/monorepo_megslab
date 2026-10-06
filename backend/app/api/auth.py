"""Routes d'authentification : inscription, connexion, invitation, profil."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import utilisateur_courant
from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.auth import (
    ConnexionDemande,
    InscriptionDemande,
    InvitationAcceptation,
    InvitationInfoReponse,
    MotDePasseModification,
    OrganisationDuProfil,
    ProfilModification,
    SessionReponse,
    UtilisateurReponse,
)
from app.services.acces_service import AccesService
from app.services.auth_service import AuthService
from app.services.team_service import TeamService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/inscription", response_model=UtilisateurReponse, status_code=201)
async def inscription(
    demande: InscriptionDemande,
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    service = AuthService(db, airbyte_client)
    utilisateur = await service.inscrire(demande.email, demande.mot_de_passe, demande.nom_complet)
    return await _profil(db, utilisateur)


@router.post("/connexion", response_model=SessionReponse)
async def connexion(demande: ConnexionDemande, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    jeton = await service.connecter(demande.email, demande.mot_de_passe)
    return SessionReponse(jeton=jeton)


@router.get("/moi", response_model=UtilisateurReponse)
async def moi(utilisateur: User = Depends(utilisateur_courant), db: AsyncSession = Depends(get_db)):
    return await _profil(db, utilisateur)


@router.patch("/moi", response_model=UtilisateurReponse)
async def modifier_profil(
    demande: ProfilModification,
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).modifier_profil(utilisateur, demande.nom_complet)
    return await _profil(db, utilisateur)


@router.post("/mot-de-passe", status_code=204)
async def changer_mot_de_passe(
    demande: MotDePasseModification,
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    await AuthService(db).changer_mot_de_passe(utilisateur, demande.actuel, demande.nouveau)


@router.get("/invitation/{jeton}", response_model=InvitationInfoReponse)
async def invitation(jeton: str, db: AsyncSession = Depends(get_db)):
    """Ce que voit la personne invitee avant d'accepter. Public : le jeton suffit."""
    invitation = await TeamService(db).invitation_valide(jeton)
    organisation = await db.get(Organization, invitation.organization_id)
    compte = await AuthService(db)._trouver_par_email(invitation.email)
    return InvitationInfoReponse(
        organisation=organisation.nom if organisation else "",
        email=invitation.email,
        role=invitation.role.value,
        compte_existant=compte is not None,
    )


@router.post("/invitation/{jeton}", response_model=SessionReponse)
async def accepter_invitation(
    jeton: str, demande: InvitationAcceptation, db: AsyncSession = Depends(get_db)
):
    """Rejoint l'organisation et ouvre directement une session."""
    utilisateur = await TeamService(db).accepter(jeton, demande.nom_complet, demande.mot_de_passe)
    return SessionReponse(jeton=AuthService(db).emettre_jeton(utilisateur))


async def _profil(db: AsyncSession, utilisateur: User) -> UtilisateurReponse:
    acces = AccesService(db)
    organisation = await acces.organisation_de(utilisateur)
    role = await acces.role_organisation(utilisateur, organisation) if organisation else None
    return UtilisateurReponse(
        id=utilisateur.id,
        email=utilisateur.email,
        nom_complet=utilisateur.nom_complet,
        est_super_admin=utilisateur.est_super_admin,
        doit_changer_mot_de_passe=utilisateur.doit_changer_mot_de_passe,
        organisation=(
            OrganisationDuProfil(id=organisation.id, nom=organisation.nom, role=role.value)
            if organisation and role
            else None
        ),
    )
