"""La configuration des modeles : ce qui s'applique, et de quoi le changer.

Deux sources coexistent. Ce qui est pose ici, en base, l'emporte ; ce qui est
vide retombe sur le fichier de deploiement. Vider un reglage rend donc
exactement le comportement precedent - il n'y a pas d'etat intermediaire ou
personne ne saurait plus ce qui s'applique. La colonne « origine » dit, pour
chaque valeur, laquelle des deux parle.

Ecrire est reserve au super-administrateur : changer le modele de l'Analyste
change la justesse de toutes les reponses suivantes.

Ce que l'API ne rend JAMAIS : la valeur d'une cle d'API. Elle est chiffree en
base et l'interface n'en recoit qu'une empreinte de quatre caracteres de chaque
cote, de quoi reconnaitre la cle sans pouvoir s'en servir.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import super_admin, utilisateur_courant
from app.core.database import get_db
from app.core.llm_client import CHAINES_PAR_AGENT, construire_la_chaine
from app.core.tarifs import CATALOGUE, tarif_de
from app.models.configuration_llm import FOURNISSEURS
from app.models.user import User
from app.schemas.configuration import (
    ChaineAgentReponse,
    ChaineDemande,
    CleDemande,
    CleReponse,
    ConfigurationModelesReponse,
    FournisseurReponse,
    ModeleDisponible,
)
from app.services.recharger_reglages import recharger
from app.services.reglages_llm_service import ReglagesLLMService

router = APIRouter(prefix="/configuration", tags=["configuration"])

ROLES = {
    "analyste": "Traduit la question en SQL. C'est lui qui determine la justesse.",
    "redacteur": "Transforme le resultat en une phrase francaise.",
    "viz": "Choisit le type de graphique, ou aucun.",
}

# Profil de jetons d'une question, mesure le 6 septembre 2026 sur dix-sept
# questions, six agents compris.
JETONS_ENTREE = 5_440
JETONS_SORTIE = 832
# Le cache d'instructions d'Anthropic a fait economiser 27 % sur cette mesure.
# Aucun fournisseur europeen n'en propose l'equivalent : la projection serait
# fausse de 27 % si on l'appliquait a tous.
ECONOMIE_CACHE = {"anthropic": 0.27}

# Les seuls modeles passes sur le jeu d'evaluation a ce jour. Tout le reste est
# un tarif sans mesure de justesse, et l'interface doit le dire.
MESURES = {("anthropic", "claude-opus-5"): "12/15 sur le jeu d'evaluation du 6 septembre 2026"}


def _cout_mille(fournisseur: str, entree: float, sortie: float) -> float:
    brut = (JETONS_ENTREE * entree + JETONS_SORTIE * sortie) / 1_000_000 * 1000
    return round(brut * (1 - ECONOMIE_CACHE.get(fournisseur, 0.0)), 2)


@router.get("/modeles", response_model=ConfigurationModelesReponse)
async def modeles(_: User = Depends(utilisateur_courant), db: AsyncSession = Depends(get_db)):
    agents = [_chaine_de(agent) for agent in CHAINES_PAR_AGENT]
    tous = [f for a in agents for f in a.fournisseurs]
    etat = await ReglagesLLMService(db).etat_des_cles()
    return ConfigurationModelesReponse(
        agents=agents,
        cles=[CleReponse(fournisseur=f, **etat[f]) for f in FOURNISSEURS],
        rabattement_actif=any(len(a.fournisseurs) > 1 for a in agents),
        entierement_europeenne=bool(tous) and all(f.dans_l_union_europeenne for f in tous),
    )


@router.get("/modeles/disponibles", response_model=list[ModeleDisponible])
async def disponibles(_: User = Depends(utilisateur_courant)):
    """Le catalogue des modeles tarifes, du moins cher au plus cher."""
    modeles = [_disponible(t) for t in CATALOGUE.values()]
    return sorted(modeles, key=lambda m: m.cout_mille_questions)


@router.put("/chaine", response_model=ConfigurationModelesReponse)
async def poser_chaine(
    demande: ChaineDemande,
    _: User = Depends(super_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ReglagesLLMService(db)
    await service.poser_chaine(demande.agent, demande.chaine)
    await recharger(db)
    return await modeles(_=None, db=db)


@router.put("/cle", response_model=ConfigurationModelesReponse)
async def poser_cle(
    demande: CleDemande,
    _: User = Depends(super_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ReglagesLLMService(db)
    await service.poser_cle(demande.fournisseur, demande.cle)
    await recharger(db)
    return await modeles(_=None, db=db)


def _chaine_de(agent: str) -> ChaineAgentReponse:
    fournisseurs = []
    for rang, nom in enumerate(construire_la_chaine(agent).noms, start=1):
        fournisseur, _, modele = nom.partition("/")
        fournisseurs.append(_decrire(rang, fournisseur, modele))
    return ChaineAgentReponse(agent=agent, role=ROLES.get(agent, ""), fournisseurs=fournisseurs)


def _decrire(rang: int, fournisseur: str, modele: str) -> FournisseurReponse:
    tarif = tarif_de(fournisseur, modele)
    ou = tarif.localisation
    return FournisseurReponse(
        rang=rang,
        fournisseur=fournisseur,
        modele=modele,
        pays=ou.pays,
        drapeau=ou.drapeau,
        ville=ou.ville,
        dans_l_union_europeenne=ou.dans_l_union_europeenne,
        localisation_verifiee=ou.verifiee,
        prix_entree_par_million=tarif.entree,
        prix_sortie_par_million=tarif.sortie,
    )


def _disponible(tarif) -> ModeleDisponible:
    ou = tarif.localisation
    return ModeleDisponible(
        fournisseur=tarif.fournisseur,
        modele=tarif.modele,
        pays=ou.pays,
        drapeau=ou.drapeau,
        ville=ou.ville,
        dans_l_union_europeenne=ou.dans_l_union_europeenne,
        localisation_verifiee=ou.verifiee,
        prix_entree_par_million=tarif.entree,
        prix_sortie_par_million=tarif.sortie,
        cout_mille_questions=_cout_mille(tarif.fournisseur, tarif.entree, tarif.sortie),
        justesse_mesuree=(tarif.fournisseur, tarif.modele) in MESURES,
        note=MESURES.get((tarif.fournisseur, tarif.modele), ""),
    )
