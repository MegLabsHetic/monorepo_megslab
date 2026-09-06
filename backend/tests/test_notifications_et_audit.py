"""Notifications adressees aux bonnes personnes, journal d'audit relisible."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_access import WorkspaceAccess
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService


async def _monde(db: AsyncSession):
    organisation = Organization(nom="Acme")
    ada = User(email="ada@example.com", nom_complet="Ada")  # owner
    bob = User(email="bob@example.com", nom_complet="Bob")  # membre avec acces
    zoe = User(email="zoe@example.com", nom_complet="Zoe")  # membre sans acces
    db.add_all([organisation, ada, bob, zoe])
    await db.flush()
    espace = Workspace(organization_id=organisation.id, nom="General", schema_entrepot="ws_x")
    db.add(espace)
    await db.flush()
    db.add_all(
        [
            Membership(user_id=ada.id, organization_id=organisation.id, role=Role.OWNER),
            Membership(user_id=bob.id, organization_id=organisation.id, role=Role.MEMBER),
            Membership(user_id=zoe.id, organization_id=organisation.id, role=Role.MEMBER),
            WorkspaceAccess(user_id=bob.id, workspace_id=espace.id, role=Role.VIEWER),
        ]
    )
    await db.flush()
    return organisation, espace, ada, bob, zoe


async def test_une_notification_d_espace_va_aux_acces_et_aux_admins_seulement(
    db: AsyncSession,
) -> None:
    organisation, espace, ada, bob, zoe = await _monde(db)
    service = NotificationService(db)

    await service.notifier_espace(espace, "sync", "Termine", "3 lignes", "/donnees/x")
    await db.commit()

    assert await service.nb_non_lues(ada) == 1  # admin de l'organisation : herite
    assert await service.nb_non_lues(bob) == 1  # acces explicite
    assert await service.nb_non_lues(zoe) == 0  # membre sans acces a cet espace

    notification = (await service.lister(bob))[0]
    assert (notification.titre, notification.lien) == ("Termine", "/donnees/x")
    await service.marquer_lue(bob, notification.id)
    assert await service.nb_non_lues(bob) == 0


async def test_tout_marquer_lu_ne_touche_que_ses_propres_notifications(db: AsyncSession) -> None:
    organisation, espace, ada, bob, _ = await _monde(db)
    service = NotificationService(db)
    await service.notifier_admins(organisation.id, "budget", "80 %", "", "/finops")
    service.creer(bob.id, "equipe", "Bienvenue")
    await db.commit()

    await service.tout_marquer_lu(ada)

    assert await service.nb_non_lues(ada) == 0
    assert await service.nb_non_lues(bob) == 1


async def test_le_journal_garde_qui_a_fait_quoi_et_se_relit_par_pages(db: AsyncSession) -> None:
    organisation, espace, ada, bob, _ = await _monde(db)
    service = AuditService(db)
    # Des horodatages distincts : dans la meme microseconde, l'ordre serait indefini.
    base = datetime(2026, 9, 6, 10, 0, tzinfo=UTC)
    for i in range(3):
        ligne = service.enregistrer(
            organisation.id, ada, "source.connectee", "source", f"s{i}", f"Base {i}", {}, espace.id
        )
        ligne.cree_le = base + timedelta(minutes=i)
    derniere = service.enregistrer(
        organisation.id, bob, "question.posee", "question", None, "Combien ?"
    )
    derniere.cree_le = base + timedelta(minutes=10)
    await db.commit()

    entrees, total = await service.lister(organisation, limite=2, avant_page=0)
    assert total == 4 and len(entrees) == 2
    assert entrees[0].ligne.action == "question.posee" and entrees[0].auteur.id == bob.id
    assert entrees[0].espace is None
    assert entrees[1].espace is not None and entrees[1].espace.nom == "General"

    suite, _ = await service.lister(organisation, limite=2, avant_page=1)
    assert [e.ligne.cible_nom for e in suite] == ["Base 1", "Base 0"]
