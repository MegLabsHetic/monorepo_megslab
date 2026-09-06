"""Journaliser une action depuis une route, en une ligne.

Les services commitent leur propre transaction ; la trace est ecrite juste
apres, dans la sienne. Si l'action a echoue, la route a leve avant d'arriver
ici : pas de trace pour une action qui n'a pas eu lieu.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.audit_service import AuditService


async def journaliser(
    db: AsyncSession,
    organisation_id: str,
    utilisateur: User,
    action: str,
    cible_type: str,
    cible_id: str | None = None,
    cible_nom: str = "",
    detail: dict | None = None,
    workspace_id: str | None = None,
) -> None:
    AuditService(db).enregistrer(
        organisation_id, utilisateur, action, cible_type, cible_id, cible_nom, detail, workspace_id
    )
    await db.commit()
