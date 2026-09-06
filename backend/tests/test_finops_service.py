"""Le rapport FinOps decoupe les couts conserves, sans en inventer."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace
from app.services.finops_service import AGENT_NON_VENTILE, FinopsService


async def _monde(db: AsyncSession) -> Organization:
    organisation = Organization(nom="Acme")
    ada = User(email="ada@example.com", nom_complet="Ada")
    bob = User(email="bob@example.com", nom_complet="Bob")
    db.add_all([organisation, ada, bob])
    await db.flush()
    finance = Workspace(organization_id=organisation.id, nom="Finance", schema_entrepot="ws_f")
    marketing = Workspace(organization_id=organisation.id, nom="Marketing", schema_entrepot="ws_m")
    db.add_all([finance, marketing])
    await db.flush()
    fil_f = Conversation(workspace_id=finance.id, user_id=ada.id, titre="Ventes")
    fil_m = Conversation(workspace_id=marketing.id, user_id=bob.id, titre="Campagnes")
    db.add_all([fil_f, fil_m])
    await db.flush()

    ventile = [
        {
            "agent": "analyste",
            "statut": "terminee",
            "duree_ms": 10,
            "detail": "",
            "cout_dollars": 0.03,
            "jetons": 300,
        },
        {
            "agent": "redacteur",
            "statut": "terminee",
            "duree_ms": 5,
            "detail": "",
            "cout_dollars": 0.01,
            "jetons": 100,
        },
    ]
    db.add_all(
        [
            Question(
                workspace_id=finance.id,
                conversation_id=fil_f.id,
                user_id=ada.id,
                texte="Q1",
                reponse="R",
                cout_dollars=0.04,
                jetons=400,
                duree_ms=1000,
                jetons_entree=250,
                jetons_sortie=50,
                jetons_cache_lus=100,
                jetons_cache_ecrits=0,
                etapes=ventile,
                cree_le=datetime(2026, 9, 3, tzinfo=UTC),
            ),
            Question(
                workspace_id=marketing.id,
                conversation_id=fil_m.id,
                user_id=bob.id,
                texte="Q2",
                reponse="R",
                cout_dollars=0.10,
                jetons=1000,
                duree_ms=3000,
                # Une question d'avant la ventilation : pas de cout par etape.
                etapes=[{"agent": "analyste", "statut": "terminee", "duree_ms": 10, "detail": ""}],
                cree_le=datetime(2026, 9, 3, tzinfo=UTC),
            ),
            Question(
                workspace_id=finance.id,
                conversation_id=fil_f.id,
                user_id=ada.id,
                texte="Q3",
                reponse="R",
                cout_dollars=0.02,
                jetons=200,
                duree_ms=2000,
                etapes=[],
                cree_le=datetime(2026, 9, 7, tzinfo=UTC),
            ),
            # Hors mois : ne doit pas apparaitre.
            Question(
                workspace_id=finance.id,
                conversation_id=fil_f.id,
                user_id=ada.id,
                texte="Q0",
                reponse="R",
                cout_dollars=9.0,
                jetons=9,
                duree_ms=1,
                etapes=[],
                cree_le=datetime(2026, 8, 30, tzinfo=UTC),
            ),
        ]
    )
    await db.flush()
    return organisation


async def test_le_rapport_decoupe_le_mois_par_jour_utilisateur_espace_et_agent(
    db: AsyncSession,
) -> None:
    organisation = await _monde(db)

    rapport = await FinopsService(db).rapport(organisation, 2026, 9)

    assert rapport.total_dollars == pytest.approx(0.16)
    assert rapport.nb_questions == 3
    assert rapport.duree_moyenne_ms == 2000
    assert [(ligne.cle, ligne.nb_questions) for ligne in rapport.par_jour] == [
        ("2026-09-03", 2),
        ("2026-09-07", 1),
    ]
    assert [(ligne.libelle, ligne.nb_questions) for ligne in rapport.par_espace] == [
        ("Marketing", 1),
        ("Finance", 2),
    ]
    assert rapport.par_utilisateur[0].libelle.startswith("Bob")
    # La part de cache : 100 jetons lus en cache sur 250 + 100 d'entree.
    assert rapport.jetons.taux_cache == pytest.approx(100 / 350)
    # Q2 et Q3 n'ont pas de cout par etape : leur total va dans « non ventile ».
    agents = {ligne.cle: ligne.cout_dollars for ligne in rapport.par_agent}
    assert agents["analyste"] == pytest.approx(0.03)
    assert agents["redacteur"] == pytest.approx(0.01)
    assert agents[AGENT_NON_VENTILE] == pytest.approx(0.12)


async def test_l_export_csv_a_une_ligne_par_question_du_mois(db: AsyncSession) -> None:
    organisation = await _monde(db)

    csv = await FinopsService(db).export_csv(organisation, 2026, 9)
    lignes = csv.strip().split("\n")

    assert lignes[0].startswith("date;espace;utilisateur;email;fil;question;cout_dollars")
    assert len(lignes) == 4
    assert "Finance;Ada;ada@example.com;Ventes;Q1;0.040000;400;1000" in lignes[1]
