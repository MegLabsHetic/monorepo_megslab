"""Routes FinOps : budget de l'organisation, rapport de couts, export, poids des donnees."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit import journaliser
from app.api.deps import organisation_administree, organisation_courante, utilisateur_courant
from app.core.database import get_db
from app.core.errors import ErreurUtilisateur
from app.models.organization import Organization
from app.models.user import User
from app.schemas.finops import (
    BudgetDemande,
    BudgetReponse,
    JetonsReponse,
    LigneReponse,
    PoidsEspaceReponse,
    RapportReponse,
)
from app.services.budget_service import BudgetService, EtatBudget
from app.services.finops_service import FinopsService, Ligne

router = APIRouter(prefix="/organisation", tags=["finops"])


@router.get("/budget", response_model=BudgetReponse)
async def budget(
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    return _budget(await BudgetService(db).etat(organisation))


@router.put("/budget", response_model=BudgetReponse)
async def definir_budget(
    demande: BudgetDemande,
    utilisateur: User = Depends(utilisateur_courant),
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    service = BudgetService(db)
    await service.definir(
        organisation, demande.budget_dollars, demande.seuil_alerte_pct, demande.bloquant
    )
    await journaliser(
        db,
        organisation.id,
        utilisateur,
        "budget.modifie",
        "organisation",
        organisation.id,
        organisation.nom,
        demande.model_dump(),
    )
    return _budget(await service.etat(organisation))


@router.get("/finops", response_model=RapportReponse)
async def rapport(
    mois: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    annee, numero = _mois(mois)
    r = await FinopsService(db).rapport(organisation, annee, numero)
    return RapportReponse(
        annee=r.annee,
        mois=r.mois,
        total_dollars=r.total_dollars,
        nb_questions=r.nb_questions,
        duree_moyenne_ms=r.duree_moyenne_ms,
        jetons=JetonsReponse(
            entree=r.jetons.entree,
            sortie=r.jetons.sortie,
            cache_lus=r.jetons.cache_lus,
            cache_ecrits=r.jetons.cache_ecrits,
            taux_cache=r.jetons.taux_cache,
        ),
        par_jour=[_ligne(ligne) for ligne in r.par_jour],
        par_utilisateur=[_ligne(ligne) for ligne in r.par_utilisateur],
        par_espace=[_ligne(ligne) for ligne in r.par_espace],
        par_agent=[_ligne(ligne) for ligne in r.par_agent],
        budget=_budget(r.budget) if r.budget else None,
    )


@router.get("/finops/export")
async def exporter(
    mois: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    organisation: Organization = Depends(organisation_administree),
    db: AsyncSession = Depends(get_db),
):
    """Le detail par question du mois, en CSV (separateur point-virgule, pour Excel)."""
    annee, numero = _mois(mois)
    contenu = await FinopsService(db).export_csv(organisation, annee, numero)
    nom = f"meglabs-couts-{annee}-{numero:02d}.csv"
    return Response(
        content="﻿" + contenu,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nom}"'},
    )


@router.get("/finops/entrepot", response_model=list[PoidsEspaceReponse])
async def poids_entrepot(
    organisation: Organization = Depends(organisation_courante),
    db: AsyncSession = Depends(get_db),
):
    """La taille des tables de chaque espace, lue dans Postgres a l'instant."""
    return [
        PoidsEspaceReponse(
            espace_id=p.espace.id, espace_nom=p.espace.nom, nb_tables=p.nb_tables, octets=p.octets
        )
        for p in await FinopsService(db).poids_entrepot(organisation)
    ]


def _mois(valeur: str | None) -> tuple[int, int]:
    if valeur is None:
        maintenant = datetime.now(UTC)
        return maintenant.year, maintenant.month
    annee, mois = (int(partie) for partie in valeur.split("-"))
    if not 1 <= mois <= 12:
        raise ErreurUtilisateur("Mois invalide.", code_http=422)
    return annee, mois


def _budget(etat: EtatBudget) -> BudgetReponse:
    return BudgetReponse(
        budget_dollars=etat.budget_dollars,
        depense_mois_dollars=etat.depense_mois_dollars,
        pourcentage=etat.pourcentage,
        seuil_alerte_pct=etat.seuil_alerte_pct,
        bloquant=etat.bloquant,
        alerte=etat.alerte,
        bloque=etat.bloque,
        jours_ecoules=round(etat.jours_ecoules, 2),
        jours_dans_le_mois=etat.jours_dans_le_mois,
        prevision_fin_de_mois_dollars=etat.prevision_fin_de_mois_dollars,
    )


def _ligne(ligne: Ligne) -> LigneReponse:
    return LigneReponse(
        cle=ligne.cle,
        libelle=ligne.libelle,
        cout_dollars=ligne.cout_dollars,
        nb_questions=ligne.nb_questions,
        jetons=ligne.jetons,
    )
