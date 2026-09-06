"""Les tableaux de bord d'un espace : epingler une reponse, rejouer ses requetes."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.ml import AgentML, AnalyseSerie
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete, Resultat
from app.core.errors import ErreurUtilisateur
from app.core.sql_guard import SqlRefuse, valider
from app.models.dashboard import NOM_MAX, Dashboard, Widget
from app.models.membership import Role
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace

WIDGETS_MAX = 24


@dataclass(frozen=True)
class WidgetVivant:
    """Un widget avec ce que sa requete vient de rendre, ou pourquoi elle a echoue."""

    widget: Widget
    resultat: Resultat | None
    analyse: AnalyseSerie | None
    erreur: str | None


class DashboardService:
    def __init__(self, db: AsyncSession, fabrique_moteur=DuckDBEngine) -> None:
        self._db = db
        self._fabrique_moteur = fabrique_moteur

    async def lister(self, espace: Workspace) -> list[tuple[Dashboard, int, User]]:
        nb_widgets = (
            select(Widget.dashboard_id, func.count().label("nb"))
            .group_by(Widget.dashboard_id)
            .subquery()
        )
        resultat = await self._db.execute(
            select(Dashboard, func.coalesce(nb_widgets.c.nb, 0), User)
            .join(User, User.id == Dashboard.user_id)
            .outerjoin(nb_widgets, nb_widgets.c.dashboard_id == Dashboard.id)
            .where(Dashboard.workspace_id == espace.id)
            .order_by(Dashboard.maj_le.desc())
        )
        return [(d, int(nb), u) for d, nb, u in resultat.all()]

    async def creer(self, espace: Workspace, utilisateur: User, nom: str) -> Dashboard:
        dashboard = Dashboard(workspace_id=espace.id, user_id=utilisateur.id, nom=_nom(nom))
        self._db.add(dashboard)
        await self._db.commit()
        await self._db.refresh(dashboard)
        return dashboard

    async def charger(self, espace: Workspace, dashboard_id: str) -> Dashboard:
        dashboard = await self._db.get(Dashboard, dashboard_id)
        if dashboard is None or dashboard.workspace_id != espace.id:
            raise ErreurUtilisateur("Tableau de bord introuvable.", code_http=404)
        return dashboard

    async def renommer(self, dashboard: Dashboard, nom: str) -> Dashboard:
        dashboard.nom = _nom(nom)
        await self._db.commit()
        await self._db.refresh(dashboard)
        return dashboard

    async def supprimer(self, dashboard: Dashboard, utilisateur: User, role: Role) -> None:
        if dashboard.user_id != utilisateur.id and role != Role.ADMIN:
            raise ErreurUtilisateur(
                "Seul l'auteur ou un admin de l'espace peut supprimer ce tableau.", code_http=403
            )
        for widget in await self._widgets(dashboard):
            await self._db.delete(widget)
        await self._db.delete(dashboard)
        await self._db.commit()

    async def epingler(self, dashboard: Dashboard, question: Question, titre: str | None) -> Widget:
        """Fait d'une reponse un widget : son SQL et son graphique, pas son resultat."""
        if question.workspace_id != dashboard.workspace_id:
            raise ErreurUtilisateur("Cette question n'appartient pas a cet espace.", 404)
        if not question.sql:
            raise ErreurUtilisateur(
                "Cette reponse n'a pas de requete a rejouer : rien a epingler.", code_http=422
            )
        existants = await self._widgets(dashboard)
        if len(existants) >= WIDGETS_MAX:
            raise ErreurUtilisateur(f"Un tableau contient au plus {WIDGETS_MAX} widgets.", 422)

        widget = Widget(
            dashboard_id=dashboard.id,
            question_id=question.id,
            titre=_nom(titre or (question.graphique or {}).get("titre") or question.texte),
            sql=question.sql,
            graphique=question.graphique,
            position=len(existants),
        )
        self._db.add(widget)
        dashboard.maj_le = datetime.now(UTC)
        await self._db.commit()
        await self._db.refresh(widget)
        return widget

    async def modifier_widget(
        self, dashboard: Dashboard, widget_id: str, titre: str | None, position: int | None
    ) -> Widget:
        widget = await self._widget(dashboard, widget_id)
        if titre is not None:
            widget.titre = _nom(titre)
        if position is not None:
            widget.position = max(0, position)
        await self._db.commit()
        await self._db.refresh(widget)
        return widget

    async def retirer_widget(self, dashboard: Dashboard, widget_id: str) -> None:
        widget = await self._widget(dashboard, widget_id)
        await self._db.delete(widget)
        await self._db.commit()

    async def rafraichir(self, espace: Workspace, dashboard: Dashboard) -> list[WidgetVivant]:
        """Rejoue chaque requete sur l'entrepot, en parallele : chaque widget a sa
        propre connexion, et une qui echoue n'empeche pas les autres."""
        widgets = await self._widgets(dashboard)
        moteur = self._fabrique_moteur(espace.schema_entrepot)
        return list(
            await asyncio.gather(*(asyncio.to_thread(_rejouer, moteur, w) for w in widgets))
        )

    async def _widgets(self, dashboard: Dashboard) -> list[Widget]:
        resultat = await self._db.execute(
            select(Widget).where(Widget.dashboard_id == dashboard.id).order_by(Widget.position)
        )
        return list(resultat.scalars())

    async def _widget(self, dashboard: Dashboard, widget_id: str) -> Widget:
        widget = await self._db.get(Widget, widget_id)
        if widget is None or widget.dashboard_id != dashboard.id:
            raise ErreurUtilisateur("Widget introuvable.", code_http=404)
        return widget


def _rejouer(moteur: DuckDBEngine, widget: Widget) -> WidgetVivant:
    """Le SQL repasse par le garde-fou : ce qui etait valide hier l'est encore,
    mais le verifier ne coute rien et ferme la porte a une modification en base."""
    try:
        resultat = moteur.executer(valider(widget.sql))
    except (SqlRefuse, ErreurRequete) as erreur:
        return WidgetVivant(widget, None, None, erreur.raison)
    try:
        analyse = AgentML().analyser(resultat)
    except (ValueError, TypeError, ArithmeticError):
        analyse = None
    return WidgetVivant(widget, resultat, analyse, None)


def _nom(texte: str) -> str:
    propre = " ".join(texte.split())
    if not propre:
        raise ErreurUtilisateur("Le nom ne peut pas etre vide.", code_http=422)
    return propre if len(propre) <= NOM_MAX else propre[: NOM_MAX - 1] + "…"
