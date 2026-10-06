"""Charger un jeu de demonstration dans un espace, en un clic.

Les tables viennent d'un schema de l'entrepot reserve a cet usage (le jeu
Olist, charge une fois pour toutes) : elles sont copiees par Postgres, sans
transiter par le serveur, puis enregistrees comme une source ordinaire. Rien
n'est telecharge, rien n'est invente : ce sont les memes tables que
n'importe quelle source synchronisee.
"""

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.data import AgentData
from app.core.config import get_settings
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete
from app.core.entrepot_writer import EntrepotWriter, ErreurImport
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource, StatutSource
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)

NOM_SOURCE_DEMO = "Jeu de demonstration Olist"
PREFIXE_DEMO = "demo_"
TYPE_DEMO = "demo"


class DemoService:
    def __init__(
        self,
        db: AsyncSession,
        fabrique_moteur=DuckDBEngine,
        fabrique_writer=EntrepotWriter,
    ) -> None:
        self._db = db
        self._fabrique_moteur = fabrique_moteur
        self._fabrique_writer = fabrique_writer

    @staticmethod
    def disponible() -> bool:
        return bool(get_settings().demo_schema)

    async def charger(self, espace: Workspace) -> DataSource:
        schema_demo = get_settings().demo_schema
        if not schema_demo:
            raise ErreurUtilisateur(
                "Aucun jeu de demonstration n'est configure sur ce serveur.", code_http=503
            )
        if await self._deja_chargee(espace):
            raise ErreurUtilisateur(
                "Le jeu de demonstration est deja present dans cet espace.", code_http=409
            )

        try:
            tables = await asyncio.to_thread(self._fabrique_moteur(schema_demo).lister_tables)
        except ErreurRequete as erreur:
            raise ErreurUtilisateur(erreur.raison, code_http=502) from erreur
        if not tables:
            raise ErreurUtilisateur("Le schema de demonstration est vide.", code_http=503)

        try:
            colonnes = await asyncio.to_thread(
                self._fabrique_writer(espace.schema_entrepot).copier_tables,
                schema_demo,
                tables,
                PREFIXE_DEMO,
            )
        except ErreurImport as erreur:
            raise ErreurUtilisateur(erreur.raison, code_http=502) from erreur

        source = DataSource(
            workspace_id=espace.id,
            nom=NOM_SOURCE_DEMO,
            type_source=TYPE_DEMO,
            statut=StatutSource.PRETE,
            schema_entrepot=espace.schema_entrepot,
            prefixe_entrepot=PREFIXE_DEMO,
            flux_decouverts=[
                {"nom": table, "namespace": "demo", "colonnes": colonnes.get(table, [])}
                for table in tables
            ],
            flux_selectionnes=list(tables),
        )
        self._db.add(source)
        await self._db.commit()
        await self._db.refresh(source)
        AgentData.oublier(espace.schema_entrepot)
        logger.info("Jeu de demonstration charge dans %s : %s table(s)", espace.id, len(tables))
        return source

    async def _deja_chargee(self, espace: Workspace) -> bool:
        resultat = await self._db.execute(
            select(DataSource.id).where(
                DataSource.workspace_id == espace.id, DataSource.type_source == TYPE_DEMO
            )
        )
        return resultat.first() is not None
