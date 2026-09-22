"""Le glossaire metier d'un espace : lecture, ecriture, et rien de plus.

Ce service ne connait ni l'entrepot ni le modele. Il rend un dictionnaire que
l'agent Data ira chercher au moment de decrire le schema.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.annotation import DESCRIPTION_MAX, AnnotationCatalogue
from app.models.user import User
from app.models.workspace import Workspace

# Au-dela, l'annotation cesse d'etre une definition et devient de la prose :
# elle couterait des jetons a chaque question sans rien clarifier.
LIMITE_PAR_ESPACE = 400


class GlossaireService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def lister(self, espace: Workspace) -> list[AnnotationCatalogue]:
        resultat = await self._db.execute(
            select(AnnotationCatalogue)
            .where(AnnotationCatalogue.workspace_id == espace.id)
            .order_by(AnnotationCatalogue.table_nom, AnnotationCatalogue.colonne_nom)
        )
        return list(resultat.scalars())

    async def definir(
        self,
        espace: Workspace,
        utilisateur: User,
        table: str,
        colonne: str,
        description: str,
    ) -> AnnotationCatalogue:
        """Pose ou remplace l'annotation d'une cible."""
        table, colonne = table.strip(), colonne.strip()
        if not table:
            raise ErreurUtilisateur("Indiquez la table que cette definition decrit.")
        description = description.strip()[:DESCRIPTION_MAX]
        if not description:
            raise ErreurUtilisateur(
                "Ecrivez une definition, ou retirez l'annotation.", code_http=422
            )

        existante = await self._trouver(espace, table, colonne)
        if existante:
            existante.description = description
            existante.user_id = utilisateur.id
            await self._db.commit()
            return existante

        await self._refuser_si_trop_nombreuses(espace)
        annotation = AnnotationCatalogue(
            workspace_id=espace.id,
            user_id=utilisateur.id,
            table_nom=table,
            colonne_nom=colonne,
            description=description,
        )
        self._db.add(annotation)
        await self._db.commit()
        return annotation

    async def retirer(self, espace: Workspace, table: str, colonne: str) -> None:
        annotation = await self._trouver(espace, table.strip(), colonne.strip())
        if annotation is None:
            raise ErreurUtilisateur("Cette definition n'existe pas.", code_http=404)
        await self._db.delete(annotation)
        await self._db.commit()

    async def pour_le_contexte(self, espace: Workspace) -> dict[tuple[str, str], str]:
        """Le glossaire sous la forme que l'agent Data attend.

        La cle est (table, colonne) ; une colonne vide designe la table.
        """
        return {(a.table_nom, a.colonne_nom): a.description for a in await self.lister(espace)}

    async def _trouver(
        self, espace: Workspace, table: str, colonne: str
    ) -> AnnotationCatalogue | None:
        resultat = await self._db.execute(
            select(AnnotationCatalogue).where(
                AnnotationCatalogue.workspace_id == espace.id,
                AnnotationCatalogue.table_nom == table,
                AnnotationCatalogue.colonne_nom == colonne,
            )
        )
        return resultat.scalar_one_or_none()

    async def _refuser_si_trop_nombreuses(self, espace: Workspace) -> None:
        deja = len(await self.lister(espace))
        if deja >= LIMITE_PAR_ESPACE:
            raise ErreurUtilisateur(
                f"Cet espace a atteint {LIMITE_PAR_ESPACE} definitions. "
                "Retirez-en avant d'en ajouter : au-dela, le contexte envoye au "
                "modele coute plus qu'il ne clarifie.",
                code_http=409,
            )
