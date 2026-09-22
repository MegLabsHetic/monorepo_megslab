"""La configuration des modeles, telle qu'elle est reellement appliquee.

Lecture seule, et c'est deliberé. Un ecran qui laisserait changer le modele
depuis le navigateur permettrait de basculer la production sur un modele dont
la justesse n'a jamais ete mesuree — sans que personne s'en apercoive, puisque
les reponses resteraient plausibles.

Ce que cette route montre n'est pas ce qui est ecrit dans le fichier de
configuration : c'est la chaine effectivement construite par le client, agent
par agent. Si les deux divergent, c'est celle-ci qui dit la verite.
"""

from fastapi import APIRouter, Depends

from app.api.deps import utilisateur_courant
from app.core.llm_client import CHAINES_PAR_AGENT, construire_la_chaine
from app.core.tarifs import tarif_de
from app.models.user import User
from app.schemas.configuration import (
    ChaineAgentReponse,
    ConfigurationModelesReponse,
    FournisseurReponse,
)

router = APIRouter(prefix="/configuration", tags=["configuration"])

ROLES = {
    "analyste": "Traduit la question en SQL. C'est lui qui determine la justesse.",
    "redacteur": "Transforme le resultat en une phrase francaise.",
    "viz": "Choisit le type de graphique, ou aucun.",
}


@router.get("/modeles", response_model=ConfigurationModelesReponse)
async def modeles(_: User = Depends(utilisateur_courant)):
    agents = [_chaine_de(agent) for agent in CHAINES_PAR_AGENT]
    tous = [f for a in agents for f in a.fournisseurs]
    return ConfigurationModelesReponse(
        agents=agents,
        rabattement_actif=any(len(a.fournisseurs) > 1 for a in agents),
        entierement_europeenne=bool(tous) and all(f.dans_l_union_europeenne for f in tous),
    )


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
