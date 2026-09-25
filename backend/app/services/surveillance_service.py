"""Les surveillances d'un espace : les declarer, et les executer.

L'execution ne fait appel a aucun modele. Elle rejoue du SQL deja valide, passe
le resultat a l'agent ML - qui est du calcul, pas de la generation - et decide
de notifier ou non. Une surveillance qui tourne chaque matin ne coute donc rien
d'autre que le temps de la requete.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.ml import AgentML
from app.core.duckdb_engine import DuckDBEngine, ErreurRequete
from app.core.errors import ErreurUtilisateur
from app.core.sql_guard import SqlRefuse, valider
from app.models.surveillance import TITRE_MAX, Declencheur, Surveillance
from app.models.user import User
from app.models.workspace import Workspace
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

SURVEILLANCES_MAX = 20


@dataclass(frozen=True)
class Verdict:
    """Ce qu'une execution a constate, et s'il faut en avertir quelqu'un."""

    surveillance: Surveillance
    notifier: bool
    message: str
    erreur: str | None = None


class SurveillanceService:
    def __init__(self, db: AsyncSession, fabrique_moteur=DuckDBEngine) -> None:
        self._db = db
        self._fabrique_moteur = fabrique_moteur

    async def lister(self, espace: Workspace) -> list[Surveillance]:
        resultat = await self._db.execute(
            select(Surveillance)
            .where(Surveillance.workspace_id == espace.id)
            .order_by(Surveillance.cree_le.desc())
        )
        return list(resultat.scalars())

    async def creer(
        self,
        espace: Workspace,
        utilisateur: User,
        titre: str,
        sql: str,
        declencheur: Declencheur,
        seuil: float | None,
        heure: int,
    ) -> Surveillance:
        titre = " ".join(titre.split())[:TITRE_MAX]
        if not titre:
            raise ErreurUtilisateur("Donnez un titre a cette surveillance.", code_http=422)
        if not 0 <= heure <= 23:
            raise ErreurUtilisateur("L'heure doit etre comprise entre 0 et 23.", code_http=422)
        if declencheur in (Declencheur.SEUIL_DEPASSE, Declencheur.SEUIL_SOUS) and seuil is None:
            raise ErreurUtilisateur(
                "Indiquez le seuil a partir duquel vous voulez etre prevenu.", code_http=422
            )
        # Le comptage ignore `active` : mettre en pause ne libere donc pas de
        # place, et le message ne doit pas envoyer l'utilisateur le croire.
        if len(await self.lister(espace)) >= SURVEILLANCES_MAX:
            raise ErreurUtilisateur(
                f"Cet espace a atteint {SURVEILLANCES_MAX} surveillances, le maximum. "
                "Supprimez-en une avant d'en creer une nouvelle.",
                code_http=409,
            )

        surveillance = Surveillance(
            workspace_id=espace.id,
            user_id=utilisateur.id,
            titre=titre,
            # Le garde-fou s'applique des la creation : on ne stocke jamais du
            # SQL qu'on n'aurait pas le droit d'executer.
            sql=self._valider(sql),
            declencheur=declencheur,
            seuil=seuil,
            heure=heure,
        )
        self._db.add(surveillance)
        await self._db.commit()
        return surveillance

    async def basculer(self, espace: Workspace, surveillance_id: str, active: bool) -> Surveillance:
        surveillance = await self.charger(espace, surveillance_id)
        surveillance.active = active
        await self._db.commit()
        return surveillance

    async def supprimer(self, espace: Workspace, surveillance_id: str) -> None:
        surveillance = await self.charger(espace, surveillance_id)
        await self._db.delete(surveillance)
        await self._db.commit()

    async def executer(self, espace: Workspace, surveillance: Surveillance) -> Verdict:
        """Rejoue la requete et decide s'il faut prevenir. Aucun appel au modele."""
        moteur = self._fabrique_moteur(espace.schema_entrepot)
        try:
            resultat = moteur.executer(valider(surveillance.sql))
        except (SqlRefuse, ErreurRequete) as erreur:
            verdict = Verdict(surveillance, False, "", erreur.raison)
            await self._consigner(surveillance, f"echec : {erreur.raison}")
            return verdict

        verdict = _juger(surveillance, resultat)
        await self._consigner(surveillance, verdict.message or "rien a signaler")
        if verdict.notifier:
            await NotificationService(self._db).notifier_espace(
                espace,
                "surveillance",
                surveillance.titre,
                verdict.message,
                "/surveillances",
            )
        return verdict

    async def _consigner(self, surveillance: Surveillance, etat: str) -> None:
        surveillance.derniere_execution = datetime.now(UTC)
        surveillance.dernier_etat = etat[:500]
        await self._db.commit()

    async def charger(self, espace: Workspace, surveillance_id: str) -> Surveillance:
        surveillance = await self._db.get(Surveillance, surveillance_id)
        if surveillance is None or surveillance.workspace_id != espace.id:
            raise ErreurUtilisateur("Surveillance introuvable.", code_http=404)
        return surveillance

    def _valider(self, sql: str) -> str:
        try:
            return valider(sql)
        except SqlRefuse as refus:
            raise ErreurUtilisateur(
                f"Cette requete a ete refusee : {refus.raison}", code_http=422
            ) from refus


def _juger(surveillance: Surveillance, resultat) -> Verdict:
    """Decide si le resultat merite une notification.

    Le declencheur par anomalie s'appuie sur l'agent ML, donc sur de la
    statistique. Les declencheurs par seuil lisent la premiere valeur numerique
    rencontree en parcourant le resultat ligne par ligne : c'est volontairement
    simple, et le titre de la surveillance doit dire ce que cette valeur
    represente.
    """
    if surveillance.declencheur is Declencheur.TOUJOURS:
        return Verdict(surveillance, True, _resume(resultat))

    if surveillance.declencheur is Declencheur.ANOMALIE:
        try:
            analyse = AgentML().analyser(resultat)
        except (ValueError, TypeError, ArithmeticError):
            analyse = None
        if analyse is None:
            return Verdict(surveillance, False, "serie non analysable")
        if analyse.anomalies:
            return Verdict(surveillance, True, analyse.resume())
        return Verdict(surveillance, False, "aucune anomalie")

    valeur = _premiere_valeur(resultat)
    if valeur is None:
        return Verdict(surveillance, False, "aucune valeur numerique")
    if surveillance.seuil is None:
        return Verdict(surveillance, False, "seuil absent")
    if surveillance.declencheur is Declencheur.SEUIL_DEPASSE and valeur > surveillance.seuil:
        return Verdict(surveillance, True, f"{valeur:g} depasse le seuil de {surveillance.seuil:g}")
    if surveillance.declencheur is Declencheur.SEUIL_SOUS and valeur < surveillance.seuil:
        return Verdict(
            surveillance, True, f"{valeur:g} est passe sous le seuil de {surveillance.seuil:g}"
        )
    return Verdict(surveillance, False, f"{valeur:g}, seuil non franchi")


def _premiere_valeur(resultat) -> float | None:
    for ligne in resultat.lignes:
        for valeur in ligne:
            if isinstance(valeur, bool):
                continue
            if isinstance(valeur, (int, float)):
                return float(valeur)
    return None


def _resume(resultat) -> str:
    valeur = _premiere_valeur(resultat)
    if valeur is not None:
        return f"{valeur:g} ({len(resultat.lignes)} ligne(s))"
    return f"{len(resultat.lignes)} ligne(s)"
