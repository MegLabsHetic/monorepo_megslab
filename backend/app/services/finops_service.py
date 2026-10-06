"""Ce que l'assistant coute, decoupe de toutes les facons utiles.

Tout part des questions conservees : leur cout mesure, leurs jetons par
nature, le passage de chaque agent. Rien n'est estime ici, sauf la prevision
de fin de mois, qui est un simple prorata et qui le dit.
"""

import asyncio
import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.duckdb_engine import DuckDBEngine, ErreurRequete
from app.models.conversation import Conversation
from app.models.organization import Organization
from app.models.question import Question
from app.models.user import User
from app.models.workspace import Workspace
from app.services.budget_service import BudgetService, EtatBudget

AGENT_NON_VENTILE = "non ventile"


@dataclass(frozen=True)
class Ligne:
    cle: str
    libelle: str
    cout_dollars: float
    nb_questions: int
    jetons: int = 0


@dataclass(frozen=True)
class Jetons:
    entree: int
    sortie: int
    cache_lus: int
    cache_ecrits: int

    @property
    def taux_cache(self) -> float | None:
        """La part des jetons d'entree servie depuis le cache de prompt."""
        base = self.entree + self.cache_lus + self.cache_ecrits
        return None if base == 0 else self.cache_lus / base


@dataclass(frozen=True)
class Rapport:
    annee: int
    mois: int
    total_dollars: float
    nb_questions: int
    duree_moyenne_ms: int
    jetons: Jetons
    par_jour: list[Ligne]
    par_utilisateur: list[Ligne]
    par_espace: list[Ligne]
    par_agent: list[Ligne]
    budget: EtatBudget | None


@dataclass(frozen=True)
class PoidsEspace:
    espace: Workspace
    nb_tables: int
    octets: int


class FinopsService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def rapport(self, organisation: Organization, annee: int, mois: int) -> Rapport:
        lignes = await self._questions_du_mois(organisation, annee, mois)
        questions = [q for q, _, _, _ in lignes]

        total = sum(q.cout_dollars for q in questions)
        maintenant = datetime.now(UTC)
        budget = (
            await BudgetService(self._db).etat(organisation)
            if (annee, mois) == (maintenant.year, maintenant.month)
            else None
        )
        return Rapport(
            annee=annee,
            mois=mois,
            total_dollars=total,
            nb_questions=len(questions),
            duree_moyenne_ms=(
                int(sum(q.duree_ms for q in questions) / len(questions)) if questions else 0
            ),
            jetons=Jetons(
                entree=sum(q.jetons_entree for q in questions),
                sortie=sum(q.jetons_sortie for q in questions),
                cache_lus=sum(q.jetons_cache_lus for q in questions),
                cache_ecrits=sum(q.jetons_cache_ecrits for q in questions),
            ),
            par_jour=_par_jour(questions),
            par_utilisateur=_regrouper(
                lignes, lambda q, u, e, c: (u.id, f"{u.nom_complet} <{u.email}>")
            ),
            par_espace=_regrouper(lignes, lambda q, u, e, c: (e.id, e.nom)),
            par_agent=_par_agent(questions),
            budget=budget,
        )

    async def export_csv(self, organisation: Organization, annee: int, mois: int) -> str:
        """Une ligne par question : de quoi refacturer en interne, ou auditer."""
        tampon = io.StringIO()
        ecrivain = csv.writer(tampon, delimiter=";", lineterminator="\n")
        ecrivain.writerow(
            [
                "date",
                "espace",
                "utilisateur",
                "email",
                "fil",
                "question",
                "cout_dollars",
                "jetons",
                "duree_ms",
            ]
        )
        for q, u, e, c in await self._questions_du_mois(organisation, annee, mois):
            ecrivain.writerow(
                [
                    q.cree_le.isoformat(timespec="seconds"),
                    e.nom,
                    u.nom_complet,
                    u.email,
                    c.titre,
                    q.texte,
                    f"{q.cout_dollars:.6f}",
                    q.jetons,
                    q.duree_ms,
                ]
            )
        return tampon.getvalue()

    async def poids_entrepot(self, organisation: Organization) -> list[PoidsEspace]:
        """La taille reelle des tables de chaque espace, lue dans Postgres.

        Ouvre l'entrepot une fois par espace : quelques secondes chacun. C'est
        pour ca que l'interface le demande a part, sur un clic.
        """
        espaces = list(
            (
                await self._db.execute(
                    select(Workspace)
                    .where(Workspace.organization_id == organisation.id)
                    .order_by(Workspace.cree_le)
                )
            ).scalars()
        )
        resultats = []
        for espace in espaces:
            try:
                tailles = await asyncio.to_thread(
                    DuckDBEngine(espace.schema_entrepot).tailles_tables
                )
            except ErreurRequete:
                tailles = []
            resultats.append(
                PoidsEspace(
                    espace=espace,
                    nb_tables=len(tailles),
                    octets=sum(octets for _, octets in tailles),
                )
            )
        return resultats

    async def _questions_du_mois(
        self, organisation: Organization, annee: int, mois: int
    ) -> list[tuple[Question, User, Workspace, Conversation]]:
        debut = datetime(annee, mois, 1, tzinfo=UTC)
        fin = datetime(annee + (mois == 12), mois % 12 + 1, 1, tzinfo=UTC)
        resultat = await self._db.execute(
            select(Question, User, Workspace, Conversation)
            .join(User, User.id == Question.user_id)
            .join(Workspace, Workspace.id == Question.workspace_id)
            .join(Conversation, Conversation.id == Question.conversation_id)
            .where(
                Workspace.organization_id == organisation.id,
                Question.cree_le >= debut,
                Question.cree_le < fin,
            )
            .order_by(Question.cree_le)
        )
        return [tuple(ligne) for ligne in resultat.all()]  # type: ignore[misc]


def _par_jour(questions: list[Question]) -> list[Ligne]:
    couts: dict[str, list[float]] = defaultdict(list)
    for q in questions:
        couts[q.cree_le.strftime("%Y-%m-%d")].append(q.cout_dollars)
    return [
        Ligne(cle=jour, libelle=jour, cout_dollars=sum(valeurs), nb_questions=len(valeurs))
        for jour, valeurs in sorted(couts.items())
    ]


def _regrouper(lignes, cle) -> list[Ligne]:
    groupes: dict[str, tuple[str, float, int, int]] = {}
    for q, u, e, c in lignes:
        identifiant, libelle = cle(q, u, e, c)
        _, cout, nb, jetons = groupes.get(identifiant, (libelle, 0.0, 0, 0))
        groupes[identifiant] = (libelle, cout + q.cout_dollars, nb + 1, jetons + q.jetons)
    return sorted(
        (
            Ligne(cle=k, libelle=v[0], cout_dollars=v[1], nb_questions=v[2], jetons=v[3])
            for k, v in groupes.items()
        ),
        key=lambda ligne: ligne.cout_dollars,
        reverse=True,
    )


def _par_agent(questions: list[Question]) -> list[Ligne]:
    """Le cout par agent, tel que chaque etape l'a enregistre.

    Les questions anterieures a la ventilation par etape n'ont que leur total :
    l'ecart apparait sous « non ventile » plutot que d'etre attribue au hasard.
    """
    couts: dict[str, float] = defaultdict(float)
    jetons: dict[str, int] = defaultdict(int)
    nb: dict[str, int] = defaultdict(int)
    for q in questions:
        ventile = 0.0
        for etape in q.etapes or []:
            cout = float(etape.get("cout_dollars", 0) or 0)
            if cout <= 0:
                continue
            couts[etape["agent"]] += cout
            jetons[etape["agent"]] += int(etape.get("jetons", 0) or 0)
            nb[etape["agent"]] += 1
            ventile += cout
        reste = q.cout_dollars - ventile
        if reste > 1e-9:
            couts[AGENT_NON_VENTILE] += reste
            nb[AGENT_NON_VENTILE] += 1
    return sorted(
        (
            Ligne(cle=a, libelle=a, cout_dollars=c, nb_questions=nb[a], jetons=jetons[a])
            for a, c in couts.items()
        ),
        key=lambda ligne: ligne.cout_dollars,
        reverse=True,
    )
