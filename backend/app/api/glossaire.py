"""Le glossaire metier d'un espace : les definitions que le schema ne porte pas.

Ecrire est reserve aux administrateurs de l'espace : une definition fausse se
propage a toutes les reponses suivantes, puisqu'elle rejoint le contexte envoye
au modele. La lecture, elle, est ouverte a tout membre — savoir ce que
« chiffre d'affaires » recouvre ici n'est pas un privilege.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AccesEspace, acces_admin_espace, acces_courant, utilisateur_courant
from app.core.database import get_db
from app.models.user import User
from app.schemas.glossaire import (
    AnnotationDemande,
    AnnotationReponse,
    GlossaireReponse,
)
from app.services.glossaire_service import GlossaireService

router = APIRouter(prefix="/espaces/{espace_id}/glossaire", tags=["glossaire"])


def _reponse(a) -> AnnotationReponse:
    return AnnotationReponse(
        id=a.id,
        table_nom=a.table_nom,
        colonne_nom=a.colonne_nom,
        description=a.description,
        porte_sur_la_table=a.porte_sur_la_table,
    )


@router.get("", response_model=GlossaireReponse)
async def lister(
    acces: AccesEspace = Depends(acces_courant),
    db: AsyncSession = Depends(get_db),
):
    annotations = await GlossaireService(db).lister(acces.espace)
    return GlossaireReponse(total=len(annotations), annotations=[_reponse(a) for a in annotations])


@router.put("", response_model=AnnotationReponse)
async def definir(
    demande: AnnotationDemande,
    acces: AccesEspace = Depends(acces_admin_espace),
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    annotation = await GlossaireService(db).definir(
        acces.espace,
        utilisateur,
        demande.table_nom,
        demande.colonne_nom,
        demande.description,
    )
    return _reponse(annotation)


@router.delete("", status_code=204)
async def retirer(
    table_nom: str,
    colonne_nom: str = "",
    acces: AccesEspace = Depends(acces_admin_espace),
    db: AsyncSession = Depends(get_db),
):
    await GlossaireService(db).retirer(acces.espace, table_nom, colonne_nom)
