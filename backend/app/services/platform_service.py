"""Ce que l'operateur de la plateforme voit : compteurs par organisation, sante.

Les tests de sante eprouvent vraiment chaque dependance : un appel a Airbyte,
une ouverture de l'entrepot. Pas de « configure donc ok ». Aucun appel au
modele en revanche : le tester couterait de l'argent a chaque affichage.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.airbyte_client import AirbyteClient
from app.core.config import get_settings
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete
from app.models.data_source import DataSource
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OrganisationVue:
    organisation: Organization
    nb_membres: int
    nb_espaces: int
    nb_sources: int
    nb_questions: int
    cout_dollars: float


@dataclass(frozen=True)
class Composant:
    nom: str
    etat: str  # "ok" | "ko" | "non_teste"
    detail: str
    latence_ms: int | None = None


@dataclass(frozen=True)
class Totaux:
    nb_organisations: int
    nb_utilisateurs: int
    cout_dollars: float


class PlatformService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def organisations(self) -> list[OrganisationVue]:
        organisations = list(
            (await self._db.execute(select(Organization).order_by(Organization.cree_le))).scalars()
        )
        membres = await self._compter(Membership.organization_id, Membership)
        espaces = await self._compter(Workspace.organization_id, Workspace)
        sources = dict(
            (
                await self._db.execute(
                    select(Workspace.organization_id, func.count(DataSource.id))
                    .join(DataSource, DataSource.workspace_id == Workspace.id)
                    .group_by(Workspace.organization_id)
                )
            ).all()
        )
        questions = {
            org_id: (int(nb), float(cout or 0))
            for org_id, nb, cout in (
                await self._db.execute(
                    select(
                        Workspace.organization_id,
                        func.count(Question.id),
                        func.sum(Question.cout_dollars),
                    )
                    .join(Question, Question.workspace_id == Workspace.id)
                    .group_by(Workspace.organization_id)
                )
            ).all()
        }
        return [
            OrganisationVue(
                organisation=o,
                nb_membres=membres.get(o.id, 0),
                nb_espaces=espaces.get(o.id, 0),
                nb_sources=int(sources.get(o.id, 0)),
                nb_questions=questions.get(o.id, (0, 0.0))[0],
                cout_dollars=questions.get(o.id, (0, 0.0))[1],
            )
            for o in organisations
        ]

    async def totaux(self) -> Totaux:
        nb_organisations = await self._db.scalar(select(func.count(Organization.id)))
        nb_utilisateurs = await self._db.scalar(select(func.count(User.id)))
        cout = await self._db.scalar(select(func.sum(Question.cout_dollars)))
        return Totaux(int(nb_organisations or 0), int(nb_utilisateurs or 0), float(cout or 0))

    async def sante(self, airbyte_client: AirbyteClient) -> list[Composant]:
        # Le premier espace reellement provisionne : un espace sans workspace
        # Airbyte (cree quand Airbyte etait injoignable) ne prouverait rien.
        premier = (
            await self._db.execute(
                select(Workspace)
                .where(Workspace.airbyte_workspace_id.is_not(None))
                .order_by(Workspace.cree_le)
                .limit(1)
            )
        ).scalar_one_or_none()
        return [
            await self._sante_airbyte(airbyte_client, premier),
            await self._sante_entrepot(premier),
            self._sante_modele(),
        ]

    async def _sante_airbyte(self, client: AirbyteClient, espace: Workspace | None) -> Composant:
        if espace is None or not espace.airbyte_workspace_id:
            return Composant("Airbyte", "non_teste", "Aucun espace provisionne a interroger.")
        depart = time.perf_counter()
        try:
            sources = await client.lister_sources(espace.airbyte_workspace_id)
        except httpx.HTTPError as erreur:
            return Composant("Airbyte", "ko", _sans_secret(str(erreur)), _ms(depart))
        return Composant(
            "Airbyte", "ok", f"{len(sources)} source(s) dans le premier espace.", _ms(depart)
        )

    async def _sante_entrepot(self, espace: Workspace | None) -> Composant:
        if espace is None:
            return Composant("Entrepot", "non_teste", "Aucun espace dont ouvrir le schema.")
        depart = time.perf_counter()
        try:
            tables = await asyncio.to_thread(DuckDBEngine(espace.schema_entrepot).lister_tables)
        except ErreurRequete as erreur:
            return Composant("Entrepot", "ko", erreur.raison, _ms(depart))
        return Composant(
            "Entrepot", "ok", f"{len(tables)} table(s) dans le premier espace.", _ms(depart)
        )

    @staticmethod
    def _sante_modele() -> Composant:
        """Configure ou non : l'eprouver reellement couterait un appel facturé."""
        if get_settings().anthropic_api_key:
            return Composant("Modele", "ok", "Cle configuree ; non appele pour ne rien facturer.")
        return Composant("Modele", "ko", "Aucune cle configuree : l'assistant repondra 503.")

    async def _compter(self, colonne, modele) -> dict[str, int]:
        lignes = await self._db.execute(select(colonne, func.count(modele.id)).group_by(colonne))
        return {cle: int(nb) for cle, nb in lignes.all()}


def _ms(depart: float) -> int:
    return int((time.perf_counter() - depart) * 1000)


def _sans_secret(message: str) -> str:
    return re.sub(r"(client_secret|password)=\S+", r"\1=***", message)[:200]
