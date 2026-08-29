"""L'equipe d'une organisation : membres, roles, invitations.

Deux facons de faire entrer quelqu'un, toutes deux sans e-mail : un lien
d'invitation que l'admin transmet lui-meme, ou un compte cree directement
avec un mot de passe temporaire a changer a la premiere connexion.
"""

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErreurUtilisateur
from app.models.invitation import Invitation
from app.models.membership import ROLES_ESPACE, ROLES_ORGANISATION, Membership, Role
from app.models.organization import Organization
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_access import WorkspaceAccess
from app.services.auth_service import hacher_mot_de_passe

DUREE_INVITATION = timedelta(days=7)


@dataclass(frozen=True)
class AccesDemande:
    workspace_id: str
    role: Role


@dataclass(frozen=True)
class Membre:
    utilisateur: User
    role: Role
    acces: list[tuple[Workspace, Role]]


class TeamService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # --- Lecture ---------------------------------------------------------------

    async def membres(self, organisation: Organization) -> list[Membre]:
        appartenances = (
            await self._db.execute(
                select(User, Membership.role)
                .join(Membership, Membership.user_id == User.id)
                .where(Membership.organization_id == organisation.id)
                .order_by(Membership.cree_le)
            )
        ).all()
        acces = (
            await self._db.execute(
                select(WorkspaceAccess.user_id, Workspace, WorkspaceAccess.role)
                .join(Workspace, Workspace.id == WorkspaceAccess.workspace_id)
                .where(Workspace.organization_id == organisation.id)
                .order_by(Workspace.cree_le)
            )
        ).all()
        par_utilisateur: dict[str, list[tuple[Workspace, Role]]] = {}
        for user_id, espace, role in acces:
            par_utilisateur.setdefault(user_id, []).append((espace, role))
        return [
            Membre(utilisateur=u, role=role, acces=par_utilisateur.get(u.id, []))
            for u, role in appartenances
        ]

    async def invitations(self, organisation: Organization) -> list[Invitation]:
        resultat = await self._db.execute(
            select(Invitation)
            .where(Invitation.organization_id == organisation.id)
            .order_by(Invitation.cree_le.desc())
        )
        return list(resultat.scalars())

    # --- Entrees dans l'equipe -------------------------------------------------

    async def inviter(
        self,
        organisation: Organization,
        email: str,
        role: Role,
        acces: list[AccesDemande],
        par: User,
    ) -> Invitation:
        self._verifier_role_organisation(role)
        await self._verifier_espaces(organisation, acces)
        if await self._role_de(organisation, email) is not None:
            raise ErreurUtilisateur("Cette personne fait deja partie de l'organisation.", 409)

        invitation = Invitation(
            organization_id=organisation.id,
            email=email.strip().lower(),
            role=role,
            acces=[{"workspace_id": a.workspace_id, "role": a.role.value} for a in acces],
            jeton=secrets.token_urlsafe(32),
            invitee_par=par.id,
            expire_le=datetime.now(UTC) + DUREE_INVITATION,
        )
        self._db.add(invitation)
        await self._db.commit()
        await self._db.refresh(invitation)
        return invitation

    async def invitation_valide(self, jeton: str) -> Invitation:
        invitation = (
            await self._db.execute(select(Invitation).where(Invitation.jeton == jeton))
        ).scalar_one_or_none()
        if invitation is None or invitation.acceptee_le is not None:
            raise ErreurUtilisateur("Cette invitation n'est plus valable.", code_http=404)
        if _aware(invitation.expire_le) < datetime.now(UTC):
            raise ErreurUtilisateur("Cette invitation a expire.", code_http=410)
        return invitation

    async def accepter(self, jeton: str, nom_complet: str | None, mot_de_passe: str | None) -> User:
        """Rejoint l'organisation : avec le compte existant portant cet e-mail,
        ou en creant le compte si c'est une premiere venue."""
        invitation = await self.invitation_valide(jeton)
        utilisateur = await self._par_email(invitation.email)
        if utilisateur is None:
            if not mot_de_passe or len(mot_de_passe) < 8 or not (nom_complet or "").strip():
                raise ErreurUtilisateur(
                    "Un nom et un mot de passe d'au moins 8 caracteres sont requis.", 422
                )
            utilisateur = User(
                email=invitation.email,
                nom_complet=nom_complet.strip(),
                mot_de_passe_hache=hacher_mot_de_passe(mot_de_passe),
            )
            self._db.add(utilisateur)
            await self._db.flush()

        await self._rattacher(invitation.organization_id, utilisateur, invitation.role)
        for entree in invitation.acces or []:
            self._db.add(
                WorkspaceAccess(
                    workspace_id=entree["workspace_id"],
                    user_id=utilisateur.id,
                    role=Role(entree["role"]),
                )
            )
        invitation.acceptee_le = datetime.now(UTC)
        await self._db.commit()
        await self._db.refresh(utilisateur)
        return utilisateur

    async def creer_membre(
        self,
        organisation: Organization,
        email: str,
        nom_complet: str,
        mot_de_passe_temporaire: str,
        role: Role,
        acces: list[AccesDemande],
    ) -> User:
        """Un compte cree par l'admin : mot de passe temporaire, a changer a la
        premiere connexion."""
        self._verifier_role_organisation(role)
        await self._verifier_espaces(organisation, acces)
        if await self._par_email(email) is not None:
            raise ErreurUtilisateur(
                "Un compte existe deja avec cet e-mail : invitez-le plutot.", code_http=409
            )
        utilisateur = User(
            email=email.strip().lower(),
            nom_complet=nom_complet.strip(),
            mot_de_passe_hache=hacher_mot_de_passe(mot_de_passe_temporaire),
            doit_changer_mot_de_passe=True,
        )
        self._db.add(utilisateur)
        await self._db.flush()
        await self._rattacher(organisation.id, utilisateur, role)
        for a in acces:
            self._db.add(
                WorkspaceAccess(workspace_id=a.workspace_id, user_id=utilisateur.id, role=a.role)
            )
        await self._db.commit()
        await self._db.refresh(utilisateur)
        return utilisateur

    async def supprimer_invitation(self, organisation: Organization, invitation_id: str) -> None:
        invitation = await self._db.get(Invitation, invitation_id)
        if invitation is None or invitation.organization_id != organisation.id:
            raise ErreurUtilisateur("Invitation introuvable.", code_http=404)
        await self._db.delete(invitation)
        await self._db.commit()

    # --- Roles -----------------------------------------------------------------

    async def changer_role(self, organisation: Organization, utilisateur: User, role: Role) -> None:
        self._verifier_role_organisation(role)
        appartenance = await self._appartenance(organisation, utilisateur)
        if appartenance.role == Role.OWNER and role != Role.OWNER:
            await self._verifier_pas_le_dernier_owner(organisation)
        appartenance.role = role
        await self._db.commit()

    async def retirer(self, organisation: Organization, utilisateur: User) -> None:
        appartenance = await self._appartenance(organisation, utilisateur)
        if appartenance.role == Role.OWNER:
            await self._verifier_pas_le_dernier_owner(organisation)
        acces = await self._db.execute(
            select(WorkspaceAccess)
            .join(Workspace, Workspace.id == WorkspaceAccess.workspace_id)
            .where(
                WorkspaceAccess.user_id == utilisateur.id,
                Workspace.organization_id == organisation.id,
            )
        )
        for entree in acces.scalars():
            await self._db.delete(entree)
        await self._db.delete(appartenance)
        await self._db.commit()

    # --- Interieur -------------------------------------------------------------

    async def _rattacher(self, organization_id: str, utilisateur: User, role: Role) -> None:
        existante = (
            await self._db.execute(
                select(Membership).where(
                    Membership.user_id == utilisateur.id,
                    Membership.organization_id == organization_id,
                )
            )
        ).scalar_one_or_none()
        if existante is None:
            self._db.add(
                Membership(user_id=utilisateur.id, organization_id=organization_id, role=role)
            )

    async def _appartenance(self, organisation: Organization, utilisateur: User) -> Membership:
        appartenance = (
            await self._db.execute(
                select(Membership).where(
                    Membership.user_id == utilisateur.id,
                    Membership.organization_id == organisation.id,
                )
            )
        ).scalar_one_or_none()
        if appartenance is None:
            raise ErreurUtilisateur("Cette personne ne fait pas partie de l'organisation.", 404)
        return appartenance

    async def _verifier_pas_le_dernier_owner(self, organisation: Organization) -> None:
        proprietaires = await self._db.execute(
            select(Membership).where(
                Membership.organization_id == organisation.id, Membership.role == Role.OWNER
            )
        )
        if len(list(proprietaires.scalars())) <= 1:
            raise ErreurUtilisateur(
                "Une organisation garde toujours au moins un proprietaire.", code_http=409
            )

    async def _verifier_espaces(
        self, organisation: Organization, acces: list[AccesDemande]
    ) -> None:
        for a in acces:
            if a.role not in ROLES_ESPACE:
                raise ErreurUtilisateur("Ce role n'existe pas dans un espace.", code_http=422)
            espace = await self._db.get(Workspace, a.workspace_id)
            if espace is None or espace.organization_id != organisation.id:
                raise ErreurUtilisateur("Espace introuvable dans cette organisation.", 404)

    @staticmethod
    def _verifier_role_organisation(role: Role) -> None:
        if role not in ROLES_ORGANISATION:
            raise ErreurUtilisateur("Ce role n'existe pas dans une organisation.", code_http=422)

    async def _role_de(self, organisation: Organization, email: str) -> Role | None:
        resultat = await self._db.execute(
            select(Membership.role)
            .join(User, User.id == Membership.user_id)
            .where(
                User.email == email.strip().lower(), Membership.organization_id == organisation.id
            )
        )
        return resultat.scalar_one_or_none()

    async def _par_email(self, email: str) -> User | None:
        resultat = await self._db.execute(select(User).where(User.email == email.strip().lower()))
        return resultat.scalar_one_or_none()


def _aware(instant: datetime) -> datetime:
    """SQLite rend des datetimes naifs ; on les relit comme de l'UTC."""
    return instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)
