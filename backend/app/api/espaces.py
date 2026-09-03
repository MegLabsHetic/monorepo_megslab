"""Routes des espaces de travail : lister, creer, renommer, gerer les acces."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    AccesEspace,
    acces_admin_espace,
    acces_courant,
    organisation_administree,
    organisation_courante,
    utilisateur_courant,
)
from app.core.airbyte_client import AirbyteClient, get_airbyte_client
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.membership import Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.espace import (
    AccesEspaceDemande,
    AccesEspaceReponse,
    EspaceCreation,
    EspaceModification,
    EspaceReponse,
)
from app.services.acces_service import AccesService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/espaces", tags=["espaces"])


def en_reponse(espace: Workspace, role: Role) -> EspaceReponse:
    return EspaceReponse(
        id=espace.id,
        nom=espace.nom,
        role=role.value,
        schema_entrepot=espace.schema_entrepot,
        lien_airbyte=lien_airbyte(espace),
        cree_le=espace.cree_le,
    )


def lien_airbyte(espace: Workspace) -> str | None:
    """Le lien vers l'espace Airbyte, pour un connecteur que le formulaire ne
    propose pas. Nul tant que l'URL publique n'est pas renseignee : mieux vaut
    ne pas proposer de lien que d'en proposer un qui ne menerait nulle part."""
    base = get_settings().airbyte_url_publique.rstrip("/")
    if not base or not espace.airbyte_workspace_id:
        return None
    return f"{base}/workspaces/{espace.airbyte_workspace_id}/source/new-source"


@router.get("", response_model=list[EspaceReponse])
async def lister(
    utilisateur: User = Depends(utilisateur_courant),
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    espaces = await AccesService(db).espaces_accessibles(utilisateur, organisation)
    return [en_reponse(espace, role) for espace, role in espaces]


@router.post("", response_model=EspaceReponse, status_code=201)
async def creer(
    demande: EspaceCreation,
    utilisateur: User = Depends(utilisateur_courant),
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    espace = await WorkspaceService(db, airbyte_client).creer(
        organisation, demande.nom.strip(), utilisateur
    )
    return en_reponse(espace, Role.ADMIN)


@router.get("/{espace_id}", response_model=EspaceReponse)
async def detail(acces: AccesEspace = Depends(acces_courant)):
    return en_reponse(acces.espace, acces.role)


@router.patch("/{espace_id}", response_model=EspaceReponse)
async def renommer(
    demande: EspaceModification,
    acces: AccesEspace = Depends(acces_admin_espace),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    espace = await WorkspaceService(db, airbyte_client).renommer(acces.espace, demande.nom)
    return en_reponse(espace, acces.role)


@router.get("/{espace_id}/acces", response_model=list[AccesEspaceReponse])
async def lister_acces(
    acces: AccesEspace = Depends(acces_admin_espace),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    """Les acces explicites. Les admins de l'organisation, qui heritent de
    l'acces, n'y figurent pas."""
    entrees = await WorkspaceService(db, airbyte_client).acces(acces.espace)
    return [
        AccesEspaceReponse(user_id=u.id, email=u.email, nom_complet=u.nom_complet, role=role.value)
        for u, role in entrees
    ]


@router.put("/{espace_id}/acces/{user_id}", status_code=204)
async def definir_acces(
    user_id: str,
    demande: AccesEspaceDemande,
    acces: AccesEspace = Depends(acces_admin_espace),
    db: AsyncSession = Depends(get_db),
    airbyte_client: AirbyteClient = Depends(get_airbyte_client),
):
    """Donne, change ou retire l'acces d'un membre de l'organisation a l'espace."""
    membre = await db.get(User, user_id)
    if (
        membre is None
        or await AccesService(db).role_organisation(membre, acces.organisation) is None
    ):
        raise ErreurUtilisateur("Cette personne ne fait pas partie de l'organisation.", 404)
    role = _role(demande.role)
    await WorkspaceService(db, airbyte_client).definir_acces(acces.espace, membre, role)


def _role(valeur: str | None) -> Role | None:
    if valeur is None:
        return None
    try:
        return Role(valeur)
    except ValueError as inconnu:
        raise ErreurUtilisateur("Ce role n'existe pas.", code_http=422) from inconnu
