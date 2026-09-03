"""workspaces, accesses, conversations, invitations

Revision ID: 4f2a9c1d7e3b
Revises: c78c96e1c6f0
Create Date: 2026-09-06 00:10:00

Les donnees existantes sont reprises : chaque organisation recoit un espace
« General » qui herite de son workspace Airbyte et de son schema d'entrepot
(donc aucune table n'est deplacee), chaque membre y recoit un acces, chaque
question existante devient une conversation a une question.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "4f2a9c1d7e3b"
down_revision: str | None = "c78c96e1c6f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _maintenant() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S.%f")


def _titre(texte: str) -> str:
    propre = " ".join((texte or "").split())
    return propre if len(propre) <= 60 else propre[:59].rstrip() + "…"


def upgrade() -> None:
    _creer_tables()
    with op.batch_alter_table("users") as b:
        b.add_column(
            sa.Column(
                "doit_changer_mot_de_passe", sa.Boolean(), nullable=False, server_default=sa.false()
            )
        )
        b.add_column(
            sa.Column("est_super_admin", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    bind = op.get_bind()
    _un_espace_par_organisation(bind)
    _rattacher_les_sources(bind)
    _rattacher_les_questions(bind)

    with op.batch_alter_table("organizations") as b:
        b.drop_column("airbyte_workspace_id")
        b.drop_column("airbyte_destination_id")


def _creer_tables() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("maj_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("nom", sa.String(255), nullable=False),
        sa.Column("airbyte_workspace_id", sa.String(64), nullable=True),
        sa.Column("airbyte_destination_id", sa.String(64), nullable=True),
        sa.Column("schema_entrepot", sa.String(64), nullable=False),
    )
    op.create_index("ix_workspaces_organization_id", "workspaces", ["organization_id"])

    op.create_table(
        "workspace_accesses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("maj_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.UniqueConstraint("user_id", "workspace_id"),
    )
    op.create_index("ix_workspace_accesses_user_id", "workspace_accesses", ["user_id"])
    op.create_index("ix_workspace_accesses_workspace_id", "workspace_accesses", ["workspace_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("maj_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("titre", sa.String(120), nullable=False),
        sa.Column("epinglee", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])

    op.create_table(
        "invitations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("maj_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "organization_id", sa.String(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("acces", sa.JSON(), nullable=False),
        sa.Column("jeton", sa.String(64), nullable=False),
        sa.Column("invitee_par", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expire_le", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acceptee_le", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_invitations_organization_id", "invitations", ["organization_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])
    op.create_index("ix_invitations_jeton", "invitations", ["jeton"], unique=True)


def _un_espace_par_organisation(bind) -> None:
    organisations = (
        bind.execute(
            sa.text(
                "SELECT id, airbyte_workspace_id, airbyte_destination_id, cree_le FROM organizations"
            )
        )
        .mappings()
        .all()
    )
    for org in organisations:
        bind.execute(
            sa.text(
                "INSERT INTO workspaces (id, cree_le, maj_le, organization_id, nom, "
                "airbyte_workspace_id, airbyte_destination_id, schema_entrepot) "
                "VALUES (:id, :cree, :maj, :org, 'General', :aw, :ad, :schema)"
            ),
            {
                "id": uuid.uuid4().hex,
                "cree": org["cree_le"] or _maintenant(),
                "maj": _maintenant(),
                "org": org["id"],
                "aw": org["airbyte_workspace_id"],
                "ad": org["airbyte_destination_id"],
                "schema": f"org_{org['id']}",
            },
        )

    appartenances = (
        bind.execute(sa.text("SELECT user_id, organization_id, role FROM memberships"))
        .mappings()
        .all()
    )
    for m in appartenances:
        # L'enum est stocke par son nom (OWNER, ADMIN...). Dans un espace, un
        # proprietaire ou admin d'organisation est admin ; les autres gardent leur role.
        role = "ADMIN" if m["role"] in ("OWNER", "ADMIN") else m["role"]
        bind.execute(
            sa.text(
                "INSERT INTO workspace_accesses (id, cree_le, maj_le, user_id, workspace_id, role) "
                "SELECT :id, :cree, :maj, :u, w.id, :r FROM workspaces w "
                "WHERE w.organization_id = :org"
            ),
            {
                "id": uuid.uuid4().hex,
                "cree": _maintenant(),
                "maj": _maintenant(),
                "u": m["user_id"],
                "org": m["organization_id"],
                "r": role,
            },
        )


def _rattacher_les_sources(bind) -> None:
    with op.batch_alter_table("data_sources") as b:
        b.add_column(sa.Column("workspace_id", sa.String(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE data_sources SET workspace_id = (SELECT w.id FROM workspaces w "
            "WHERE w.organization_id = data_sources.organization_id)"
        )
    )
    with op.batch_alter_table("data_sources") as b:
        b.alter_column("workspace_id", existing_type=sa.String(), nullable=False)
        b.create_foreign_key("fk_data_sources_workspace_id", "workspaces", ["workspace_id"], ["id"])
        b.create_index("ix_data_sources_workspace_id", ["workspace_id"])
        b.drop_column("organization_id")


def _rattacher_les_questions(bind) -> None:
    with op.batch_alter_table("questions") as b:
        b.add_column(sa.Column("workspace_id", sa.String(), nullable=True))
        b.add_column(sa.Column("conversation_id", sa.String(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE questions SET workspace_id = (SELECT w.id FROM workspaces w "
            "WHERE w.organization_id = questions.organization_id)"
        )
    )
    questions = (
        bind.execute(sa.text("SELECT id, workspace_id, user_id, texte, cree_le FROM questions"))
        .mappings()
        .all()
    )
    for q in questions:
        conversation_id = uuid.uuid4().hex
        bind.execute(
            sa.text(
                "INSERT INTO conversations (id, cree_le, maj_le, workspace_id, user_id, titre, epinglee) "
                "VALUES (:id, :cree, :maj, :w, :u, :titre, 0)"
            ),
            {
                "id": conversation_id,
                "cree": q["cree_le"] or _maintenant(),
                "maj": q["cree_le"] or _maintenant(),
                "w": q["workspace_id"],
                "u": q["user_id"],
                "titre": _titre(q["texte"]),
            },
        )
        bind.execute(
            sa.text("UPDATE questions SET conversation_id = :c WHERE id = :id"),
            {"c": conversation_id, "id": q["id"]},
        )
    with op.batch_alter_table("questions") as b:
        b.alter_column("workspace_id", existing_type=sa.String(), nullable=False)
        b.alter_column("conversation_id", existing_type=sa.String(), nullable=False)
        b.create_foreign_key("fk_questions_workspace_id", "workspaces", ["workspace_id"], ["id"])
        b.create_foreign_key(
            "fk_questions_conversation_id", "conversations", ["conversation_id"], ["id"]
        )
        b.create_index("ix_questions_workspace_id", ["workspace_id"])
        b.create_index("ix_questions_conversation_id", ["conversation_id"])
        b.drop_index("ix_questions_organization_id")
        b.drop_column("organization_id")


def downgrade() -> None:
    """Retour en arriere au mieux : on ne garde que le premier espace de chaque
    organisation, et les conversations disparaissent (les questions restent)."""
    bind = op.get_bind()
    with op.batch_alter_table("organizations") as b:
        b.add_column(sa.Column("airbyte_workspace_id", sa.String(64), nullable=True))
        b.add_column(sa.Column("airbyte_destination_id", sa.String(64), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE organizations SET "
            "airbyte_workspace_id = (SELECT w.airbyte_workspace_id FROM workspaces w "
            "WHERE w.organization_id = organizations.id ORDER BY w.cree_le LIMIT 1), "
            "airbyte_destination_id = (SELECT w.airbyte_destination_id FROM workspaces w "
            "WHERE w.organization_id = organizations.id ORDER BY w.cree_le LIMIT 1)"
        )
    )
    for table in ("questions", "data_sources"):
        with op.batch_alter_table(table) as b:
            b.add_column(sa.Column("organization_id", sa.String(), nullable=True))
        bind.execute(
            sa.text(
                f"UPDATE {table} SET organization_id = (SELECT w.organization_id FROM workspaces w "
                f"WHERE w.id = {table}.workspace_id)"
            )
        )
    with op.batch_alter_table("questions") as b:
        b.alter_column("organization_id", existing_type=sa.String(), nullable=False)
        b.create_index("ix_questions_organization_id", ["organization_id"])
        b.drop_index("ix_questions_conversation_id")
        b.drop_index("ix_questions_workspace_id")
        b.drop_column("conversation_id")
        b.drop_column("workspace_id")
    with op.batch_alter_table("data_sources") as b:
        b.alter_column("organization_id", existing_type=sa.String(), nullable=False)
        b.drop_index("ix_data_sources_workspace_id")
        b.drop_column("workspace_id")
    with op.batch_alter_table("users") as b:
        b.drop_column("est_super_admin")
        b.drop_column("doit_changer_mot_de_passe")
    op.drop_table("invitations")
    op.drop_table("conversations")
    op.drop_table("workspace_accesses")
    op.drop_table("workspaces")
