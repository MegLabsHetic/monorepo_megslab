"""Depot d'un fichier comme source de donnees.

Chemin volontairement distinct des connecteurs : un fichier n'a pas de systeme
externe a interroger, donc pas de source ni de connexion Airbyte. Il est ecrit
directement dans l'entrepot, et apparait ensuite comme n'importe quelle autre
source — meme fiche, meme explorateur, memes profils.
"""

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.data import AgentData
from app.core.entrepot_writer import (
    EXTENSIONS_ACCEPTEES,
    EntrepotWriter,
    ErreurImport,
    nom_de_table,
)
from app.core.errors import ErreurUtilisateur
from app.models.data_source import DataSource, StatutSource, TypeSource
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)

TAILLE_MAX_OCTETS = 500 * 1024 * 1024
# Le fichier est ecrit sur disque par morceaux : un depot de 500 Mo ne doit pas
# occuper 500 Mo de memoire, et surtout pas x fois cela en cas de depots
# simultanes. A cette taille, l'import se compte en minutes — l'interface doit
# le dire, sinon l'attente passe pour une panne.
TAILLE_MORCEAU = 1024 * 1024


class FileSourceService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def importer_fichier(self, espace: Workspace, depot: UploadFile) -> DataSource:
        nom_fichier = depot.filename or "fichier"
        self._verifier_format(nom_fichier)

        table = nom_de_table(nom_fichier)
        prefixe = f"f{uuid.uuid4().hex[:8]}_"
        schema = espace.schema_entrepot

        lignes, colonnes = await self._ecrire_dans_entrepot(
            schema, f"{prefixe}{table}", nom_fichier, depot
        )

        source = DataSource(
            workspace_id=espace.id,
            nom=nom_fichier,
            type_source=TypeSource.FICHIER.value,
            statut=StatutSource.PRETE,
            schema_entrepot=schema,
            prefixe_entrepot=prefixe,
            flux_decouverts=[{"nom": table, "namespace": "fichier", "colonnes": colonnes}],
            flux_selectionnes=[table],
        )
        self._db.add(source)
        await self._db.commit()
        await self._db.refresh(source)
        # Une table de plus dans l'entrepot : l'assistant doit le relire.
        AgentData.oublier(schema)

        logger.info("Fichier %s importe : %s lignes dans %s", nom_fichier, lignes, schema)
        return source

    def _verifier_format(self, nom_fichier: str) -> None:
        extension = Path(nom_fichier).suffix.lower()
        if extension not in EXTENSIONS_ACCEPTEES:
            acceptees = ", ".join(sorted(EXTENSIONS_ACCEPTEES))
            raise ErreurUtilisateur(
                f"Format non pris en charge. Formats acceptes : {acceptees}.", code_http=415
            )

    async def _ecrire_dans_entrepot(
        self, schema: str, table: str, nom_fichier: str, depot: UploadFile
    ) -> tuple[int, list[str]]:
        """Ecrit le depot sur disque le temps de l'import, puis l'efface.

        Le moteur lit depuis un chemin, pas depuis de la memoire ; le fichier
        temporaire ne doit pas survivre a l'operation, meme en cas d'echec.
        """
        extension = Path(nom_fichier).suffix.lower()
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / f"depot{extension}"
            await self._copier_sur_disque(depot, chemin)
            try:
                return await asyncio.to_thread(EntrepotWriter(schema).importer, chemin, table)
            except ErreurImport as erreur:
                raise ErreurUtilisateur(erreur.raison, code_http=422) from erreur

    async def _copier_sur_disque(self, depot: UploadFile, destination: Path) -> None:
        """Recopie le depot morceau par morceau, en s'arretant des le depassement.

        La taille annoncee par le client n'est jamais fiable : on compte ce qui
        arrive vraiment, et on abandonne avant d'avoir tout ecrit plutot que de
        decouvrir la taille une fois le fichier entier accepte.
        """
        ecrits = 0
        with destination.open("wb") as sortie:
            while morceau := await depot.read(TAILLE_MORCEAU):
                ecrits += len(morceau)
                if ecrits > TAILLE_MAX_OCTETS:
                    limite = TAILLE_MAX_OCTETS // (1024 * 1024)
                    raise ErreurUtilisateur(
                        f"Ce fichier depasse la taille maximale de {limite} Mo.", code_http=413
                    )
                sortie.write(morceau)

        if ecrits == 0:
            raise ErreurUtilisateur("Ce fichier est vide.", code_http=422)
