"""Un lien de partage donne a voir des chiffres, jamais la structure du client."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.duckdb_engine import Resultat
from app.core.errors import ErreurUtilisateur
from app.models.conversation import Conversation
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace
from app.services.dashboard_service import DashboardService


class FauxMoteur:
    def __init__(self, schema: str) -> None:
        self.schema_entrepot = schema

    def executer(self, sql: str, lignes_max: int = 5000) -> Resultat:
        return Resultat(colonnes=["mois", "ventes"], lignes=[("2024-01", 100.0)], tronque=False)


async def _tableau(db: AsyncSession):
    organisation = Organization(nom="Acme")
    ada = User(email="ada@example.com", nom_complet="Ada")
    db.add_all([organisation, ada])
    await db.flush()
    espace = Workspace(organization_id=organisation.id, nom="General", schema_entrepot="ws_x")
    db.add(espace)
    await db.flush()
    fil = Conversation(workspace_id=espace.id, user_id=ada.id)
    db.add(fil)
    await db.flush()
    question = Question(
        workspace_id=espace.id,
        conversation_id=fil.id,
        user_id=ada.id,
        texte="Ventes ?",
        reponse="...",
        sql='SELECT mois, ventes FROM entrepot."ventes"',
    )
    db.add(question)
    await db.flush()
    service = DashboardService(db, FauxMoteur)
    tableau = await service.creer(espace, ada, "Pilotage")
    await service.epingler(tableau, question, "Ventes")
    return service, espace, tableau


async def test_un_tableau_neuf_n_est_pas_partage(db: AsyncSession) -> None:
    _, _, tableau = await _tableau(db)
    assert tableau.jeton_partage is None


async def test_partager_rend_un_jeton_long_et_imprevisible(db: AsyncSession) -> None:
    service, _, tableau = await _tableau(db)
    jeton = await service.partager(tableau)
    assert len(jeton) >= 40
    assert tableau.id not in jeton, "le jeton ne doit pas deriver de l'identifiant"


async def test_regenerer_revoque_le_lien_precedent(db: AsyncSession) -> None:
    service, _, tableau = await _tableau(db)
    ancien = await service.partager(tableau)
    nouveau = await service.partager(tableau)
    assert ancien != nouveau
    with pytest.raises(ErreurUtilisateur) as leve:
        await service.par_jeton(ancien)
    assert leve.value.code_http == 404


async def test_cesser_de_partager_ferme_le_lien(db: AsyncSession) -> None:
    service, _, tableau = await _tableau(db)
    jeton = await service.partager(tableau)
    await service.cesser_de_partager(tableau)
    with pytest.raises(ErreurUtilisateur):
        await service.par_jeton(jeton)


async def test_un_jeton_inconnu_et_un_jeton_revoque_rendent_la_meme_erreur(
    db: AsyncSession,
) -> None:
    """On ne revele pas qu'un lien a existe puis a ete ferme."""
    service, _, tableau = await _tableau(db)
    jeton = await service.partager(tableau)
    await service.cesser_de_partager(tableau)
    messages = []
    for essai in (jeton, "jamais-emis", ""):
        with pytest.raises(ErreurUtilisateur) as leve:
            await service.par_jeton(essai)
        messages.append((leve.value.message, leve.value.code_http))
    assert len(set(messages)) == 1


async def test_le_lien_rejoue_les_requetes_a_chaque_consultation(db: AsyncSession) -> None:
    """Un lien partage montre l'etat actuel des donnees, pas une capture."""
    service, espace, tableau = await _tableau(db)
    jeton = await service.partager(tableau)
    retrouve, espace_retrouve = await service.par_jeton(jeton)
    vivants = await service.rafraichir(espace_retrouve, retrouve)
    assert espace_retrouve.id == espace.id
    assert [v.resultat.lignes for v in vivants] == [[("2024-01", 100.0)]]
