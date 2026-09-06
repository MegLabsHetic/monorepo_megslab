"""Le journal d'audit de l'organisation, pour ses administrateurs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import organisation_administree
from app.core.database import get_db
from app.models.organization import Organization
from app.schemas.notification import EntreeJournalReponse, JournalReponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/organisation/journal", tags=["journal"])


@router.get("", response_model=JournalReponse)
async def lister(
    page: int = Query(default=0, ge=0),
    limite: int = Query(default=50, ge=1, le=200),
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    entrees, total = await AuditService(db).lister(organisation, limite, page)
    return JournalReponse(
        total=total,
        page=page,
        entrees=[
            EntreeJournalReponse(
                id=e.ligne.id,
                action=e.ligne.action,
                cible_type=e.ligne.cible_type,
                cible_id=e.ligne.cible_id,
                cible_nom=e.ligne.cible_nom,
                detail=e.ligne.detail or {},
                auteur=e.auteur.nom_complet,
                auteur_email=e.auteur.email,
                espace=e.espace.nom if e.espace else None,
                cree_le=e.ligne.cree_le,
            )
            for e in entrees
        ],
    )
