"""Lecture de l'entrepot pour une source donnee : tables, apercu, profil.

Le moteur DuckDB est synchrone et une ouverture d'entrepot coute quelques
secondes : chaque operation est donc renvoyee dans un thread, sinon elle
bloquerait la boucle d'evenements de tout le serveur pendant ce temps.
"""

import asyncio

from app.core.duckdb_engine import DuckDBEngine, ErreurRequete, Resultat, TableProfil
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource


class WarehouseService:
    def __init__(self, source: DataSource) -> None:
        self._source = source
        self._moteur = DuckDBEngine(source.schema_entrepot)

    async def lister_tables(self) -> list[tuple[str, int]]:
        """Les tables de cette source, avec leur nombre de lignes reel.

        Toutes les sources d'une organisation partagent son schema d'entrepot,
        ou leurs tables cohabitent sous des prefixes differents : on ne rend
        donc que celles de CETTE source, sous leur nom logique.
        """
        selectionnes = self._source.flux_selectionnes or []
        if not selectionnes:
            return []

        inventaire = dict(await self._dans_un_thread(self._moteur.inventaire))
        return [
            (flux, inventaire[self._source.table_entrepot(flux)])
            for flux in selectionnes
            if self._source.table_entrepot(flux) in inventaire
        ]

    async def apercu(self, table: str, limite: int = 50) -> Resultat:
        return await self._dans_un_thread(
            self._moteur.apercu, self._table_de_cette_source(table), limite
        )

    async def profiler(self, table: str) -> list[dict]:
        return await self._dans_un_thread(self._moteur.profiler, self._table_de_cette_source(table))

    async def sante(self) -> list[tuple[str, TableProfil]]:
        """Le profil de chaque table synchronisee de cette source, sous son nom logique."""
        selectionnes = self._source.flux_selectionnes or []
        if not selectionnes:
            return []
        noms = {self._source.table_entrepot(flux): flux for flux in selectionnes}
        profils = await self._dans_un_thread(self._moteur.profil_tables, list(noms))
        return [(noms[profil.nom], profil) for profil in profils]

    def _table_de_cette_source(self, table: str) -> str:
        """Traduit un nom de flux en nom de table d'entrepot, en refusant ce qui
        n'appartient pas a cette source.

        Le moteur verifie deja que la table existe dans le schema de
        l'organisation ; ce controle-ci est plus etroit : la bonne organisation,
        mais la mauvaise source, doit aussi etre refusee.
        """
        if table not in (self._source.flux_selectionnes or []):
            raise ErreurUtilisateur(
                f"La table « {table} » ne fait pas partie de cette source.", code_http=404
            )
        return self._source.table_entrepot(table)

    @staticmethod
    async def _dans_un_thread(operation, *arguments):
        try:
            return await asyncio.to_thread(operation, *arguments)
        except ErreurRequete as erreur:
            raise ErreurUtilisateur(erreur.raison, code_http=502) from erreur
