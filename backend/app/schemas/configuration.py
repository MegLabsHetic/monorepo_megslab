"""Contrats de la route de configuration des modeles, en lecture seule."""

from pydantic import BaseModel


class FournisseurReponse(BaseModel):
    """Un maillon de la chaine d'un agent, avec son prix et son pays."""

    rang: int
    fournisseur: str
    modele: str
    pays: str
    drapeau: str
    ville: str
    dans_l_union_europeenne: bool
    # Vrai quand la localisation a ete constatee et non declaree.
    localisation_verifiee: bool
    prix_entree_par_million: float
    prix_sortie_par_million: float


class ChaineAgentReponse(BaseModel):
    """La chaine d'un agent : le premier repond, les suivants sont le secours."""

    agent: str
    role: str
    fournisseurs: list[FournisseurReponse]


class ConfigurationModelesReponse(BaseModel):
    agents: list[ChaineAgentReponse]
    # Vrai quand au moins un agent a plus d'un fournisseur.
    rabattement_actif: bool
    # Vrai quand toute la chaine, pour tous les agents, reste dans l'UE.
    entierement_europeenne: bool
