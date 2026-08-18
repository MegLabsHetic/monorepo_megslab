"""Ce que l'interface a besoin de savoir sur l'organisation courante."""

from fastapi import APIRouter, Depends

from app.api.deps import organisation_courante
from app.core.config import get_settings
from app.models.organization import Organization
from app.schemas.organisation import OrganisationReponse

router = APIRouter(prefix="/organisation", tags=["organisation"])


@router.get("", response_model=OrganisationReponse)
async def detail(organisation: Organization = Depends(organisation_courante)):
    return OrganisationReponse(
        id=organisation.id,
        nom=organisation.nom,
        lien_airbyte=_lien_espace(organisation),
    )


def _lien_espace(organisation: Organization) -> str | None:
    """Le lien vers l'espace Airbyte de l'organisation.

    Nul tant que l'URL publique n'est pas renseignee : mieux vaut ne pas
    proposer de lien que d'en proposer un qui ne menerait nulle part.
    """
    base = get_settings().airbyte_url_publique.rstrip("/")
    if not base or not organisation.airbyte_workspace_id:
        return None
    return f"{base}/workspaces/{organisation.airbyte_workspace_id}/source/new-source"
