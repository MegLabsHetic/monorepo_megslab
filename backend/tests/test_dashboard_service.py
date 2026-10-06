"""Un tableau de bord epingle des requetes et les rejoue, chacune derriere le garde-fou."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.duckdb_engine import Resultat
from app.core.errors import ErreurUtilisateur
from app.models.conversation import Conversation
from app.models.dashboard import Widget
from app.models.membership import Role
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace
from app.services.dashboard_service import DashboardService


class FauxMoteur:
    """Rend une serie mensuelle de douze points pour toute requete."""

    def __init__(self, schema: str) -> None:
        self.schema_entrepot = schema
        self.requetes: list[str] = []

    def executer(self, sql: str, lignes_max: int = 5000) -> Resultat:
        self.requetes.append(sql)
        return Resultat(
            colonnes=["mois", "ventes"],
            lignes=[(f"2024-{m:02d}", 100.0 + 10 * m) for m in range(1, 13)],
            tronque=False,
        )


async def _monde(db: AsyncSession):
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
        texte="Ventes par mois ?",
        reponse="...",
        sql='SELECT mois, ventes FROM entrepot."ventes"',
        graphique={
            "type": "lignes",
            "axe_x": "mois",
            "axes_y": ["ventes"],
            "titre": "Ventes",
            "raison": "",
        },
    )
    sans_sql = Question(
        workspace_id=espace.id,
        conversation_id=fil.id,
        user_id=ada.id,
        texte="?",
        reponse="non",
        sql=None,
    )
    db.add_all([question, sans_sql])
    await db.flush()
    return espace, ada, question, sans_sql


async def test_epingler_puis_rejouer_rend_des_resultats_frais_avec_l_analyse(
    db: AsyncSession,
) -> None:
    espace, ada, question, _ = await _monde(db)
    moteurs: list[FauxMoteur] = []

    def fabrique(schema: str) -> FauxMoteur:
        moteur = FauxMoteur(schema)
        moteurs.append(moteur)
        return moteur

    service = DashboardService(db, fabrique)  # type: ignore[arg-type]
    tableau = await service.creer(espace, ada, "  Suivi   commercial ")
    widget = await service.epingler(tableau, question, None)

    assert tableau.nom == "Suivi commercial"
    assert widget.titre == "Ventes"  # le titre du graphique de la reponse
    assert widget.sql == question.sql and widget.graphique == question.graphique

    vivants = await service.rafraichir(espace, tableau)

    assert len(vivants) == 1 and vivants[0].erreur is None
    assert vivants[0].resultat is not None and vivants[0].resultat.nb_lignes == 12
    assert vivants[0].analyse is not None and vivants[0].analyse.tendance == "hausse"
    # Le SQL est repasse par le garde-fou avant d'atteindre le moteur.
    assert moteurs[0].requetes == ['SELECT mois, ventes FROM entrepot."ventes"']
    assert [(d.nom, nb) for d, nb, _ in await service.lister(espace)] == [("Suivi commercial", 1)]


async def test_une_reponse_sans_requete_ne_s_epingle_pas(db: AsyncSession) -> None:
    espace, ada, _, sans_sql = await _monde(db)
    service = DashboardService(db, FauxMoteur)  # type: ignore[arg-type]
    tableau = await service.creer(espace, ada, "Test")

    with pytest.raises(ErreurUtilisateur) as capture:
        await service.epingler(tableau, sans_sql, None)
    assert capture.value.code_http == 422


async def test_un_widget_dont_le_sql_a_ete_altere_est_refuse_sans_casser_le_tableau(
    db: AsyncSession,
) -> None:
    espace, ada, question, _ = await _monde(db)
    service = DashboardService(db, FauxMoteur)  # type: ignore[arg-type]
    tableau = await service.creer(espace, ada, "Test")
    await service.epingler(tableau, question, "Sain")
    db.add(
        Widget(
            dashboard_id=tableau.id, titre="Altere", sql='DELETE FROM entrepot."ventes"', position=1
        )
    )
    await db.flush()

    vivants = await service.rafraichir(espace, tableau)

    assert [v.widget.titre for v in vivants] == ["Sain", "Altere"]
    assert vivants[0].erreur is None
    assert vivants[1].resultat is None and "lecture" in (vivants[1].erreur or "")


async def test_seul_l_auteur_ou_un_admin_supprime(db: AsyncSession) -> None:
    espace, ada, _, _ = await _monde(db)
    bob = User(email="bob@example.com", nom_complet="Bob")
    db.add(bob)
    await db.flush()
    service = DashboardService(db, FauxMoteur)  # type: ignore[arg-type]
    tableau = await service.creer(espace, ada, "Test")

    with pytest.raises(ErreurUtilisateur):
        await service.supprimer(tableau, bob, Role.MEMBER)
    await service.supprimer(tableau, bob, Role.ADMIN)

    assert await service.lister(espace) == []
