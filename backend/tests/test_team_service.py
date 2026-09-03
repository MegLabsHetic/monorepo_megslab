"""Invitations, creation directe, roles : l'equipe d'une organisation."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.membership import Membership, Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_access import WorkspaceAccess
from app.services.team_service import AccesDemande, TeamService


async def _organisation(db: AsyncSession) -> tuple[Organization, User, Workspace]:
    organisation = Organization(nom="Acme")
    proprietaire = User(email="ada@example.com", nom_complet="Ada")
    db.add_all([organisation, proprietaire])
    await db.flush()
    espace = Workspace(organization_id=organisation.id, nom="General", schema_entrepot="ws_x")
    db.add(espace)
    await db.flush()
    db.add(Membership(user_id=proprietaire.id, organization_id=organisation.id, role=Role.OWNER))
    await db.flush()
    return organisation, proprietaire, espace


async def test_une_invitation_acceptee_cree_le_compte_et_ouvre_les_acces(db: AsyncSession) -> None:
    organisation, ada, espace = await _organisation(db)
    service = TeamService(db)

    invitation = await service.inviter(
        organisation,
        "Bob@Example.com",
        Role.MEMBER,
        [AccesDemande(workspace_id=espace.id, role=Role.VIEWER)],
        par=ada,
    )
    assert invitation.email == "bob@example.com"
    assert len(invitation.jeton) > 30

    bob = await service.accepter(invitation.jeton, "Bob", "mot-de-passe-solide")

    assert bob.email == "bob@example.com" and bob.mot_de_passe_hache is not None
    appartenance = (
        await db.execute(select(Membership).where(Membership.user_id == bob.id))
    ).scalar_one()
    assert appartenance.role == Role.MEMBER
    acces = (
        await db.execute(select(WorkspaceAccess).where(WorkspaceAccess.user_id == bob.id))
    ).scalar_one()
    assert (acces.workspace_id, acces.role) == (espace.id, Role.VIEWER)
    # Le jeton ne sert qu'une fois.
    with pytest.raises(ErreurUtilisateur):
        await service.invitation_valide(invitation.jeton)


async def test_un_compte_existant_rejoint_sans_nouveau_mot_de_passe(db: AsyncSession) -> None:
    organisation, ada, espace = await _organisation(db)
    bob = User(email="bob@example.com", nom_complet="Bob", mot_de_passe_hache="h")
    db.add(bob)
    await db.flush()
    service = TeamService(db)
    invitation = await service.inviter(organisation, "bob@example.com", Role.ADMIN, [], par=ada)

    rejoint = await service.accepter(invitation.jeton, None, None)

    assert rejoint.id == bob.id and rejoint.mot_de_passe_hache == "h"
    membres = await service.membres(organisation)
    assert {m.utilisateur.email: m.role for m in membres} == {
        "ada@example.com": Role.OWNER,
        "bob@example.com": Role.ADMIN,
    }


async def test_une_invitation_expiree_est_refusee(db: AsyncSession) -> None:
    organisation, ada, _ = await _organisation(db)
    service = TeamService(db)
    invitation = await service.inviter(organisation, "bob@example.com", Role.MEMBER, [], par=ada)
    invitation.expire_le = datetime.now(UTC) - timedelta(minutes=1)
    await db.commit()

    with pytest.raises(ErreurUtilisateur) as capture:
        await service.accepter(invitation.jeton, "Bob", "mot-de-passe-solide")
    assert capture.value.code_http == 410


async def test_inviter_un_membre_deja_present_est_refuse(db: AsyncSession) -> None:
    organisation, ada, _ = await _organisation(db)
    with pytest.raises(ErreurUtilisateur) as capture:
        await TeamService(db).inviter(organisation, "ada@example.com", Role.MEMBER, [], par=ada)
    assert capture.value.code_http == 409


async def test_un_compte_cree_par_l_admin_doit_changer_son_mot_de_passe(db: AsyncSession) -> None:
    organisation, _, espace = await _organisation(db)

    bob = await TeamService(db).creer_membre(
        organisation,
        "bob@example.com",
        "Bob",
        "temporaire-123",
        Role.MEMBER,
        [AccesDemande(workspace_id=espace.id, role=Role.MEMBER)],
    )

    assert bob.doit_changer_mot_de_passe
    assert bob.mot_de_passe_hache != "temporaire-123"


async def test_le_dernier_proprietaire_ne_peut_etre_ni_retrograde_ni_retire(
    db: AsyncSession,
) -> None:
    organisation, ada, _ = await _organisation(db)
    service = TeamService(db)

    with pytest.raises(ErreurUtilisateur):
        await service.changer_role(organisation, ada, Role.MEMBER)
    with pytest.raises(ErreurUtilisateur):
        await service.retirer(organisation, ada)


async def test_retirer_un_membre_efface_aussi_ses_acces_aux_espaces(db: AsyncSession) -> None:
    organisation, ada, espace = await _organisation(db)
    service = TeamService(db)
    bob = await service.creer_membre(
        organisation,
        "bob@example.com",
        "Bob",
        "temporaire-123",
        Role.MEMBER,
        [AccesDemande(workspace_id=espace.id, role=Role.MEMBER)],
    )

    await service.retirer(organisation, bob)

    restants = (
        (await db.execute(select(WorkspaceAccess).where(WorkspaceAccess.user_id == bob.id)))
        .scalars()
        .all()
    )
    assert restants == []
    assert [m.utilisateur.id for m in await service.membres(organisation)] == [ada.id]
