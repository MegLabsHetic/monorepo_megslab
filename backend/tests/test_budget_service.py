"""Le budget mensuel : mesure, alerte, blocage, prorata."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.conversation import Conversation
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace
from app.services.budget_service import BudgetService


@dataclass
class Monde:
    organisation: Organization
    espace: Workspace
    fil: Conversation
    utilisateur: User


async def _monde(db: AsyncSession, couts: list[float], quand: datetime) -> Monde:
    organisation = Organization(nom="Acme")
    utilisateur = User(email="ada@example.com", nom_complet="Ada")
    db.add_all([organisation, utilisateur])
    await db.flush()
    espace = Workspace(organization_id=organisation.id, nom="General", schema_entrepot="ws_x")
    db.add(espace)
    await db.flush()
    fil = Conversation(workspace_id=espace.id, user_id=utilisateur.id)
    db.add(fil)
    await db.flush()
    monde = Monde(organisation, espace, fil, utilisateur)
    for cout in couts:
        _depenser(db, monde, cout, quand)
    await db.flush()
    return monde


def _depenser(db: AsyncSession, monde: Monde, cout: float, quand: datetime) -> None:
    db.add(
        Question(
            workspace_id=monde.espace.id,
            conversation_id=monde.fil.id,
            user_id=monde.utilisateur.id,
            texte="q",
            reponse="r",
            cout_dollars=cout,
            cree_le=quand,
        )
    )


async def test_sans_budget_rien_ne_bloque_et_le_prorata_est_calcule(db: AsyncSession) -> None:
    le_10 = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    monde = await _monde(db, [1.0, 2.0], le_10)

    etat = await BudgetService(db).etat(monde.organisation, maintenant=le_10)

    assert etat.depense_mois_dollars == 3.0
    assert etat.pourcentage is None and not etat.alerte and not etat.bloque
    # 3 $ en 9,5 jours sur un mois de 30 jours.
    assert etat.jours_dans_le_mois == 30
    assert etat.prevision_fin_de_mois_dollars == pytest.approx(3.0 / 9.5 * 30)


async def test_les_depenses_du_mois_precedent_ne_comptent_pas(db: AsyncSession) -> None:
    monde = await _monde(db, [50.0], datetime(2026, 8, 20, tzinfo=UTC))

    etat = await BudgetService(db).etat(
        monde.organisation, maintenant=datetime(2026, 9, 5, tzinfo=UTC)
    )

    assert etat.depense_mois_dollars == 0.0


async def test_l_alerte_puis_le_blocage_suivent_le_budget(db: AsyncSession) -> None:
    maintenant = datetime(2026, 9, 15, tzinfo=UTC)
    monde = await _monde(db, [8.5], maintenant)
    service = BudgetService(db)
    await service.definir(
        monde.organisation, budget_dollars=10.0, seuil_alerte_pct=80, bloquant=True
    )

    etat = await service.etat(monde.organisation, maintenant=maintenant)
    assert etat.pourcentage == pytest.approx(85.0)
    assert etat.alerte and not etat.bloque

    _depenser(db, monde, 2.0, maintenant)
    await db.flush()

    with pytest.raises(ErreurUtilisateur) as capture:
        await service.verifier_avant_question(monde.organisation)
    assert capture.value.code_http == 402
    assert "10.00 $" in capture.value.message


async def test_en_mode_alerte_seule_on_ne_bloque_jamais(db: AsyncSession) -> None:
    maintenant = datetime(2026, 9, 15, tzinfo=UTC)
    monde = await _monde(db, [12.0], maintenant)
    service = BudgetService(db)
    await service.definir(
        monde.organisation, budget_dollars=10.0, seuil_alerte_pct=80, bloquant=False
    )

    etat = await service.verifier_avant_question(monde.organisation)

    assert etat.alerte and not etat.bloque


async def test_un_budget_negatif_ou_un_seuil_absurde_sont_refuses(db: AsyncSession) -> None:
    monde = await _monde(db, [], datetime(2026, 9, 1, tzinfo=UTC))
    service = BudgetService(db)
    with pytest.raises(ErreurUtilisateur):
        await service.definir(monde.organisation, -1.0, 80, True)
    with pytest.raises(ErreurUtilisateur):
        await service.definir(monde.organisation, 10.0, 0, True)
