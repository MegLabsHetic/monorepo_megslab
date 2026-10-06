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


class CleReponse(BaseModel):
    """L'etat d'une cle d'API. Jamais sa valeur."""

    fournisseur: str
    definie: bool
    # « base », « environnement » ou « illisible ».
    origine: str
    # De quoi reconnaitre la cle, pas de quoi s'en servir.
    empreinte: str


class ConfigurationModelesReponse(BaseModel):
    agents: list[ChaineAgentReponse]
    cles: list[CleReponse]
    # Vrai quand au moins un agent a plus d'un fournisseur.
    rabattement_actif: bool
    # Vrai quand toute la chaine, pour tous les agents, reste dans l'UE.
    entierement_europeenne: bool
    # Vrai quand tous les fournisseurs de tous les agents calculent en France.
    # Distinct du precedent : IONOS est europeen mais allemand, et le badge ne
    # doit pas ecrire « calcule en France » pour une chaine qui passe par lui.
    entierement_en_france: bool = False
    # L'infrastructure - serveur, entrepot, ingestion - est en France quoi
    # qu'il arrive. Seul l'appel au modele peut en sortir.
    infrastructure_en_france: bool = True


class ChaineDemande(BaseModel):
    agent: str
    # Vide : l'agent retombe sur la configuration de deploiement.
    chaine: str = ""


class CleDemande(BaseModel):
    fournisseur: str
    # Vide : la cle est retiree de la base, l'environnement reprend la main.
    cle: str = ""


class ModeleDisponible(BaseModel):
    """Un modele qu'on peut choisir, avec ce qu'on sait de lui."""

    fournisseur: str
    modele: str
    pays: str
    drapeau: str
    ville: str
    dans_l_union_europeenne: bool
    localisation_verifiee: bool
    prix_entree_par_million: float
    prix_sortie_par_million: float
    cout_mille_questions: float
    # Vrai seulement pour les modeles passes sur le jeu d'evaluation.
    justesse_mesuree: bool
    note: str = ""
