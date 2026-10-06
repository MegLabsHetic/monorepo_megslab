"""Ecrire et relire le journal d'audit.

Enregistrer ne commite pas : l'action et sa trace partent dans la meme
transaction que l'appelant, ou pas du tout. Une trace sans action, ou une
action sans trace, seraient toutes deux des mensonges.
"""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace

PAGE_MAX = 200


@dataclass(frozen=True)
class Entree:
    ligne: AuditLog
    auteur: User
    espace: Workspace | None


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    def enregistrer(
        self,
        organisation_id: str,
        utilisateur: User,
        action: str,
        cible_type: str,
        cible_id: str | None = None,
        cible_nom: str = "",
        detail: dict | None = None,
        workspace_id: str | None = None,
    ) -> AuditLog:
        ligne = AuditLog(
            organization_id=organisation_id,
            workspace_id=workspace_id,
            user_id=utilisateur.id,
            action=action,
            cible_type=cible_type,
            cible_id=cible_id,
            cible_nom=cible_nom[:255],
            detail=detail or {},
        )
        self._db.add(ligne)
        return ligne

    async def lister(
        self, organisation: Organization, limite: int = 100, avant_page: int = 0
    ) -> tuple[list[Entree], int]:
        """Les entrees les plus recentes d'abord, par pages, avec le total."""
        limite = max(1, min(limite, PAGE_MAX))
        total = await self._db.scalar(
            select(func.count(AuditLog.id)).where(AuditLog.organization_id == organisation.id)
        )
        resultat = await self._db.execute(
            select(AuditLog, User, Workspace)
            .join(User, User.id == AuditLog.user_id)
            .outerjoin(Workspace, Workspace.id == AuditLog.workspace_id)
            .where(AuditLog.organization_id == organisation.id)
            .order_by(AuditLog.cree_le.desc())
            .offset(avant_page * limite)
            .limit(limite)
        )
        return [Entree(ligne, auteur, espace) for ligne, auteur, espace in resultat.all()], int(
            total or 0
        )
