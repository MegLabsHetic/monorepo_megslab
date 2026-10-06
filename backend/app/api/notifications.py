"""Routes des notifications de l'utilisateur courant."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import utilisateur_courant
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationReponse, NotificationsReponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsReponse)
async def lister(
    utilisateur: User = Depends(utilisateur_courant), db: AsyncSession = Depends(get_db)
):
    service = NotificationService(db)
    return NotificationsReponse(
        non_lues=await service.nb_non_lues(utilisateur),
        notifications=[
            NotificationReponse(
                id=n.id,
                type=n.type,
                titre=n.titre,
                corps=n.corps,
                lien=n.lien,
                lue=n.lue,
                cree_le=n.cree_le,
            )
            for n in await service.lister(utilisateur)
        ],
    )


@router.post("/{notification_id}/lue", status_code=204)
async def marquer_lue(
    notification_id: str,
    utilisateur: User = Depends(utilisateur_courant),
    db: AsyncSession = Depends(get_db),
):
    await NotificationService(db).marquer_lue(utilisateur, notification_id)


@router.post("/toutes-lues", status_code=204)
async def tout_marquer_lu(
    utilisateur: User = Depends(utilisateur_courant), db: AsyncSession = Depends(get_db)
):
    await NotificationService(db).tout_marquer_lu(utilisateur)
