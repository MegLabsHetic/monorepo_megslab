"""Le budget mensuel d'une organisation, et ce qu'il autorise encore.

Le controle est fait par le code, avant tout appel au modele : un budget
depasse en mode bloquant refuse la question, il ne se contente pas de
l'afficher. La depense du mois est la somme des questions de tous les
espaces de l'organisation depuis le premier du mois, en UTC.
"""

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.organization import Organization
from app.models.question import Question
from app.models.workspace import Workspace

SEUIL_ALERTE_DEFAUT = 80


@dataclass(frozen=True)
class EtatBudget:
    budget_dollars: float | None
    depense_mois_dollars: float
    seuil_alerte_pct: int
    bloquant: bool
    jours_ecoules: float
    jours_dans_le_mois: int
    prevision_fin_de_mois_dollars: float

    @property
    def pourcentage(self) -> float | None:
        if not self.budget_dollars:
            return None
        return 100.0 * self.depense_mois_dollars / self.budget_dollars

    @property
    def alerte(self) -> bool:
        return self.pourcentage is not None and self.pourcentage >= self.seuil_alerte_pct

    @property
    def bloque(self) -> bool:
        return self.bloquant and self.pourcentage is not None and self.pourcentage >= 100.0


class BudgetService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def etat(
        self, organisation: Organization, maintenant: datetime | None = None
    ) -> EtatBudget:
        maintenant = maintenant or datetime.now(UTC)
        debut_mois = datetime(maintenant.year, maintenant.month, 1, tzinfo=UTC)
        depense = await self._depense_depuis(organisation, debut_mois)

        jours_dans_le_mois = calendar.monthrange(maintenant.year, maintenant.month)[1]
        # Au moins un jour ecoule : le 1er a 8 h, projeter sur un tiers de
        # journee donnerait un chiffre absurde.
        jours_ecoules = max(1.0, (maintenant - debut_mois).total_seconds() / 86_400)
        prevision = depense / jours_ecoules * jours_dans_le_mois

        return EtatBudget(
            budget_dollars=organisation.budget_mensuel_dollars,
            depense_mois_dollars=depense,
            seuil_alerte_pct=organisation.seuil_alerte_pct,
            bloquant=organisation.budget_bloquant,
            jours_ecoules=jours_ecoules,
            jours_dans_le_mois=jours_dans_le_mois,
            prevision_fin_de_mois_dollars=prevision,
        )

    async def verifier_avant_question(self, organisation: Organization) -> EtatBudget:
        """A appeler avant d'appeler le modele. Refuse si le budget est atteint."""
        etat = await self.etat(organisation)
        if etat.bloque:
            raise ErreurUtilisateur(
                f"Budget mensuel de {etat.budget_dollars:.2f} $ atteint "
                f"({etat.depense_mois_dollars:.2f} $ depenses ce mois). Un administrateur "
                "de l'organisation peut le relever dans les parametres.",
                code_http=402,
            )
        return etat

    async def definir(
        self,
        organisation: Organization,
        budget_dollars: float | None,
        seuil_alerte_pct: int,
        bloquant: bool,
    ) -> Organization:
        if budget_dollars is not None and budget_dollars < 0:
            raise ErreurUtilisateur("Le budget ne peut pas etre negatif.", code_http=422)
        if not 1 <= seuil_alerte_pct <= 100:
            raise ErreurUtilisateur("Le seuil d'alerte est un pourcentage entre 1 et 100.", 422)
        organisation.budget_mensuel_dollars = budget_dollars
        organisation.seuil_alerte_pct = seuil_alerte_pct
        organisation.budget_bloquant = bloquant
        await self._db.commit()
        await self._db.refresh(organisation)
        return organisation

    async def _depense_depuis(self, organisation: Organization, depuis: datetime) -> float:
        total = await self._db.scalar(
            select(func.sum(Question.cout_dollars))
            .join(Workspace, Workspace.id == Question.workspace_id)
            .where(Workspace.organization_id == organisation.id, Question.cree_le >= depuis)
        )
        return float(total or 0.0)
