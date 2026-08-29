"""Routes d'organisation : fiche, equipe, invitations."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import organisation_administree, organisation_courante, utilisateur_courant
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.invitation import Invitation
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.equipe import (
    AccesDemandeSchema,
    AccesMembreReponse,
    InvitationDemande,
    InvitationReponse,
    MembreCreation,
    MembreReponse,
    RoleModification,
)
from app.schemas.organisation import OrganisationModification, OrganisationReponse
from app.services.acces_service import AccesService
from app.services.organization_service import OrganizationService
from app.services.team_service import AccesDemande, Membre, TeamService

router = APIRouter(prefix="/organisation", tags=["organisation"])


@router.get("", response_model=OrganisationReponse)
async def detail(
    utilisateur: User = Depends(utilisateur_courant),
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    role = await AccesService(db).role_organisation(utilisateur, organisation)
    nb_espaces = await db.scalar(
        select(func.count()).where(Workspace.organization_id == organisation.id)
    )
    nb_membres = await db.scalar(
        select(func.count()).where(Membership.organization_id == organisation.id)
    )
    return OrganisationReponse(
        id=organisation.id,
        nom=organisation.nom,
        role=(role or Role.MEMBER).value,
        nb_espaces=int(nb_espaces or 0),
        nb_membres=int(nb_membres or 0),
    )


@router.patch("", response_model=OrganisationReponse)
async def renommer(
    demande: OrganisationModification,
    utilisateur: User = Depends(utilisateur_courant),
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    await OrganizationService(db, airbyte_client=None).renommer(organisation, demande.nom)  # type: ignore[arg-type]
    return await detail(utilisateur, organisation, db)


# --- Membres -------------------------------------------------------------------


@router.get("/membres", response_model=list[MembreReponse])
async def lister_membres(
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    return [_membre(m) for m in await TeamService(db).membres(organisation)]


@router.post("/membres", response_model=MembreReponse, status_code=201)
async def creer_membre(
    demande: MembreCreation,
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    """Un compte cree directement par l'admin, avec un mot de passe temporaire."""
    service = TeamService(db)
    utilisateur = await service.creer_membre(
        organisation,
        demande.email,
        demande.nom_complet,
        demande.mot_de_passe_temporaire,
        _role(demande.role),
        _acces(demande.acces),
    )
    membres = await service.membres(organisation)
    return _membre(next(m for m in membres if m.utilisateur.id == utilisateur.id))


@router.patch("/membres/{user_id}", status_code=204)
async def changer_role(
    user_id: str,
    demande: RoleModification,
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    await TeamService(db).changer_role(
        organisation, await _utilisateur(db, user_id), _role(demande.role)
    )


@router.delete("/membres/{user_id}", status_code=204)
async def retirer_membre(
    user_id: str,
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    await TeamService(db).retirer(organisation, await _utilisateur(db, user_id))


# --- Invitations ---------------------------------------------------------------


@router.get("/invitations", response_model=list[InvitationReponse])
async def lister_invitations(
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    return [_invitation(i) for i in await TeamService(db).invitations(organisation)]


@router.post("/invitations", response_model=InvitationReponse, status_code=201)
async def inviter(
    demande: InvitationDemande,
    utilisateur: User = Depends(utilisateur_courant),
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    invitation = await TeamService(db).inviter(
        organisation, demande.email, _role(demande.role), _acces(demande.acces), utilisateur
    )
    return _invitation(invitation)


@router.delete("/invitations/{invitation_id}", status_code=204)
async def annuler_invitation(
    invitation_id: str,
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    await TeamService(db).supprimer_invitation(organisation, invitation_id)


# --- Interieur -----------------------------------------------------------------


def _membre(membre: Membre) -> MembreReponse:
    u = membre.utilisateur
    return MembreReponse(
        id=u.id,
        email=u.email,
        nom_complet=u.nom_complet,
        role=membre.role.value,
        actif=u.actif,
        doit_changer_mot_de_passe=u.doit_changer_mot_de_passe,
        acces=[
            AccesMembreReponse(espace_id=espace.id, espace_nom=espace.nom, role=role.value)
            for espace, role in membre.acces
        ],
        cree_le=u.cree_le,
    )


def _invitation(invitation: Invitation) -> InvitationReponse:
    return InvitationReponse(
        id=invitation.id,
        email=invitation.email,
        role=invitation.role.value,
        acces=[
            AccesDemandeSchema(espace_id=a["workspace_id"], role=a["role"])
            for a in invitation.acces or []
        ],
        jeton=invitation.jeton,
        expire_le=invitation.expire_le,
        acceptee_le=invitation.acceptee_le,
        cree_le=invitation.cree_le,
    )


def _role(valeur: str) -> Role:
    try:
        return Role(valeur)
    except ValueError as inconnu:
        raise ErreurUtilisateur("Ce role n'existe pas.", code_http=422) from inconnu


def _acces(entrees: list[AccesDemandeSchema]) -> list[AccesDemande]:
    return [AccesDemande(workspace_id=e.espace_id, role=_role(e.role)) for e in entrees]


async def _utilisateur(db: AsyncSession, user_id: str) -> User:
    utilisateur = await db.get(User, user_id)
    if utilisateur is None:
        raise ErreurUtilisateur("Utilisateur introuvable.", code_http=404)
    return utilisateur
